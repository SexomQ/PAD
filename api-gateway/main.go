package main

import (
	"errors"
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

	// Saga initiation
	builder := &saga.OrchestrationBuilder{}

	builder.AddStep(
		func(args ...interface{}) (interface{}, error) {
			fmt.Println("Executing step 1")
			return "Step 1 result", nil
		},
		func(args ...interface{}) error {
			fmt.Println("Compensating step 1")
			return nil
		},
	).AddStep(
		func(args ...interface{}) (interface{}, error) {
			fmt.Println("Executing step 2")
			return "Step 2 result", nil
		},
		func(args ...interface{}) error {
			fmt.Println("Compensating step 2")
			return nil
		},
	).AddStep(
		func(args ...interface{}) (interface{}, error) {
			fmt.Println("Executing step 3")
			return nil, errors.New("step 3 failed")
		},
		func(args ...interface{}) error {
			fmt.Println("Compensating step 3")
			return errors.New("compensation step 2 failed")
		},
	)

	builtSaga := builder.Build()
	// Saga execution route
	r.HandleFunc("/api/execute_saga", func(w http.ResponseWriter, r *http.Request) {
		err := builtSaga.Execute()
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
