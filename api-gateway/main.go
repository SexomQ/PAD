package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"gateway/handlers"
	"gateway/load_balancers"
	"gateway/middleware"
	"gateway/saga"
	"log"
	"net/http"

	"github.com/gorilla/mux"
)

func main() {

	// Initialize Redis
	middleware.InitRedis()

	// Update the service cache
	go load_balancers.PeriodicallyUpdateServiceCache()

	// Create a new router
	r := mux.NewRouter()

	// Status endpoint gateway
	r.HandleFunc("/api/status", handlers.StatusHandler)

	// Status endpoint service discovery
	r.HandleFunc("/api/service_discovery", handlers.ServiceDiscoveryHandler)

	// User-related routes
	r.PathPrefix("/api/user/").HandlerFunc(handlers.UserHandler)

	// Calendar-related routes
	r.PathPrefix("/api/calendar/").HandlerFunc(handlers.CalendarHandler)

	// Check all records in Redis
	r.HandleFunc("/api/redis", middleware.CheckRedis)

	r.HandleFunc("/api/execute_saga", func(w http.ResponseWriter, r *http.Request) {
		// Step 1: Parse JSON payload
		var payload saga.SagaPayload
		err := json.NewDecoder(r.Body).Decode(&payload)
		if err != nil {
			http.Error(w, "Invalid JSON payload", http.StatusBadRequest)
			return
		}

		// Step 2: Build the saga
		builder := &saga.OrchestrationBuilder{}

		builder.AddStep(
			func(args ...interface{}) (interface{}, error) {
				fmt.Println("Executing step 1: Login")

				// Extract payload from arguments
				userPayload := args[0].(saga.SagaPayload)

				// Create JSON payload for the login request
				loginPayload, _ := json.Marshal(map[string]string{
					"username": userPayload.Username,
					"password": userPayload.Password,
				})

				serviceName := "user-management-service"
				serviceURL := load_balancers.RoundRobinLoadBalancer(serviceName)
				if serviceURL == "" {
					return nil, fmt.Errorf("service not in queue")
				}

				// Perform the HTTP POST request
				resp, err := http.Post(serviceURL+"/api/user/login", "application/json", bytes.NewBuffer(loginPayload))
				if err != nil {
					return nil, fmt.Errorf("failed to execute step 1: %v", err)
				}
				defer resp.Body.Close()

				// Check the status code
				if resp.StatusCode != http.StatusOK {
					return nil, fmt.Errorf("step 1 failed: received status code %d", resp.StatusCode)
				}

				return "Step 1 result", nil
			},
			func(args ...interface{}) error {
				fmt.Println("Compensating step 1")
				// Add compensation logic here
				return nil
			},
		).AddStep(
			func(args ...interface{}) (interface{}, error) {
				fmt.Println("Executing step 2")

				userPayload := args[0].(saga.SagaPayload)

				// Create JSON payload for the login request
				statusPayload, _ := json.Marshal(map[string]string{
					"username": userPayload.Username,
				})

				serviceName := "calendar-service"
				serviceURL := load_balancers.RoundRobinLoadBalancer(serviceName)
				if serviceURL == "" {
					return nil, fmt.Errorf("service not in queue")
				}

				// Perform the HTTP GET request
				resp, err := http.Post(serviceURL+"/api/calendar/status", "application/json", bytes.NewBuffer(statusPayload))
				if err != nil {
					return nil, fmt.Errorf("failed to execute step 2: %v", err)
				}
				defer resp.Body.Close()

				// Check the status code
				if resp.StatusCode != http.StatusOK {
					return nil, fmt.Errorf("step 2 failed: received status code %d", resp.StatusCode)
				}

				return "Step 2 result", nil
			},
			func(args ...interface{}) error {
				fmt.Println("Compensating step 2")
				// Add compensation logic here
				return nil
			},
		)

		// Build the saga
		builtSaga := builder.Build()

		// Step 3: Execute the saga with the payload
		err = builtSaga.Execute(saga.SagaPayload(payload))
		if err != nil {
			http.Error(w, fmt.Sprintf("Saga failed: %v", err), http.StatusInternalServerError)
			return
		}

		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Saga executed successfully"))
	})

	// Start the server
	http.Handle("/", r)
	log.Println("Starting Gateway on port 8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
