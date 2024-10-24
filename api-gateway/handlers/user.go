package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"gateway/circuit_breaker"
	"gateway/load_balancers"
	"gateway/middleware"
	"io"
	"net/http"
	"time"
)

var (
	userServiceBreaker = circuit_breaker.NewCircuitBreaker(3, 30*time.Second) // Set limit and timeout
)

func UserHandler(w http.ResponseWriter, r *http.Request) {
	serviceName := "user-management-service"

	serviceURL := load_balancers.RoundRobinLoadBalancer(serviceName)
	if serviceURL == "" {
		http.Error(w, "Service not in Queue", http.StatusNotFound)
		return
	}

	target := fmt.Sprintf("%s%s", serviceURL, r.RequestURI)

	// circuit breaker
	err := userServiceBreaker.Call(func() error {
		// Simulate a 500 error for testing
		if SimulateError(r) {
			return errors.New("simulated service failure with 500 error")
		}

		req, err := http.NewRequest(r.Method, target, r.Body)
		if err != nil {
			return err
		}

		// Forward headers
		for k, v := range r.Header {
			req.Header.Set(k, v[0])
		}

		// Set timeouts
		client := &http.Client{
			Timeout: 5 * time.Second,
		}
		resp, err := client.Do(req)
		if err != nil {
			return err
		}
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)

		// If it's a login, extract the token and store it in Redis
		if r.URL.Path == "/api/user/login" && resp.StatusCode == http.StatusOK {
			var data map[string]string
			json.Unmarshal(body, &data)
			if token, ok := data["token"]; ok {
				// Assuming username is also in the response for unique token storage
				if username, exists := data["username"]; exists {
					// Cache token in Redis with username as key
					ctx := context.Background()
					key := fmt.Sprintf("jwt_token_%s", username) // Store with unique username
					err := middleware.RedisClient.Set(ctx, key, token, 24*time.Hour).Err()
					if err != nil {
						return errors.New("Failed to store token in Redis")
					}
				} else {
					return errors.New("Username missing in login response")

				}
			} else {
				return errors.New("Token missing in login response")
			}
		}

		w.WriteHeader(resp.StatusCode)
		w.Write(body)
		return nil
	})
	if err != nil {
		// If the circuit breaker is tripped, or an error occurs, return service unavailable
		http.Error(w, "Service unavailable due to circuit breaker: "+err.Error(), http.StatusServiceUnavailable)
	}
}

// Simulate a condition to trigger a 500 error
func SimulateError(r *http.Request) bool {
	return r.URL.Query().Get("simulateError") == "true"
}
