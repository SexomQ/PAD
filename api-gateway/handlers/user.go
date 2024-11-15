package handlers

import (
	"bytes"
	"fmt"
	"gateway/circuit_breaker"
	"gateway/load_balancers"
	"io"
	"net/http"
	"time"
)

// var (
// 	userServiceBreaker = circuit_breaker.NewCircuitBreaker(3, 30*time.Second) // Set limit and timeout
// )

func UserHandler(w http.ResponseWriter, r *http.Request) {
	serviceName := "user-management-service"

	// Buffer the original request body
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusInternalServerError)
		return
	}
	r.Body.Close() // Close the original body since it has been read

	// Maximum retry attempts
	const maxRetries = 3
	var attempt int

	for attempt = 1; attempt <= maxRetries; attempt++ {
		// Get a new service URL on each attempt
		serviceURL := load_balancers.RoundRobinLoadBalancer(serviceName)
		if serviceURL == "" {
			http.Error(w, "Service not in Queue", http.StatusNotFound)
			return
		}

		target := fmt.Sprintf("%s%s", serviceURL, r.RequestURI)

		// Reset the body for the retry
		r.Body = io.NopCloser(bytes.NewReader(bodyBytes)) // Recreate the body for each retry

		var userServiceBreaker = circuit_breaker.NewCircuitBreaker(3, 30*time.Second)

		// Attempt the request with the circuit breaker
		err = userServiceBreaker.Call(func() error {
			// Create a new HTTP request
			req, err := http.NewRequest(r.Method, target, r.Body)
			if err != nil {
				return err
			}

			// Forward all headers, including credentials, from the original request
			for headerName, headerValues := range r.Header {
				for _, value := range headerValues {
					req.Header.Add(headerName, value)
				}
			}

			// Set timeouts
			client := &http.Client{
				Timeout: 2 * time.Second,
			}

			// Send the request
			resp, err := client.Do(req)
			if err != nil {
				return err
			}
			defer resp.Body.Close()

			// Read the response body
			body, _ := io.ReadAll(resp.Body)

			// Write the response back to the client
			w.WriteHeader(resp.StatusCode)
			w.Write(body)
			return nil
		})

		// Break the loop if the request succeeds
		if err == nil {
			return
		}

		// Log the error for each attempt
		fmt.Printf("Attempt %d failed with service %s: %s\n", attempt, serviceURL, err.Error())
	}

	// If all attempts fail, return service unavailable
	http.Error(w, "Service unavailable after retries: "+err.Error(), http.StatusServiceUnavailable)
}

// Simulate a condition to trigger a 500 error
func SimulateError(r *http.Request) bool {
	return r.URL.Query().Get("simulateError") == "true"
}
