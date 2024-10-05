package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"gateway/middleware"
	"io"
	"net/http"
	"time"
)

func UserHandler(w http.ResponseWriter, r *http.Request) {
	serviceURL := "http://user-management-service:5001"
	target := fmt.Sprintf("%s%s", serviceURL, r.RequestURI)

	req, err := http.NewRequest(r.Method, target, r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
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
		http.Error(w, err.Error(), http.StatusGatewayTimeout)
		return
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
					http.Error(w, "Failed to store token in Redis", http.StatusInternalServerError)
					return
				}
			} else {
				http.Error(w, "Username missing in login response", http.StatusInternalServerError)
				return
			}
		}
	}

	w.WriteHeader(resp.StatusCode)
	w.Write(body)
}
