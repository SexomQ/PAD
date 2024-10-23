package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/go-redis/redis/v8"
)

var ctx = context.Background()

type RequestBody struct {
	Username         string `json:"username"`
	CalendarName     string `json:"calendar_name"`
	CalendarPassword string `json:"calendar_password"`
}

type Event struct {
	Username     string `json:"username"`
	EventName    string `json:"event_name"`
	EventStart   string `json:"event_start"`
	EventEnd     string `json:"event_end"`
	CalendarName string `json:"calendar_name"`
}

func CalendarHandler(w http.ResponseWriter, r *http.Request) {
	// Check if the request body is empty
	if r.Body == nil {
		http.Error(w, "Request body is empty", http.StatusBadRequest)
		return
	}

	// Read the request body
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusInternalServerError)
		return
	}
	defer r.Body.Close()

	var username string

	if r.URL.Path == "/api/calendar/create_event" {
		var event Event
		err = json.Unmarshal(bodyBytes, &event)
		if err != nil {
			http.Error(w, "Invalid request body", http.StatusBadRequest)
			return

		}
		if event.EventName == "" || event.EventStart == "" || event.EventEnd == "" || event.CalendarName == "" {
			http.Error(w, "Missing event details", http.StatusBadRequest)
			return
		}
		username = event.Username
		if username == "" {
			http.Error(w, "Username not provided", http.StatusBadRequest)
			return
		}
	} else {
		// Parse the JSON body to extract the username
		var requestBody RequestBody
		err = json.Unmarshal(bodyBytes, &requestBody)
		if err != nil {
			http.Error(w, "Invalid request body", http.StatusBadRequest)
			return
		}

		username = requestBody.Username
		if username == "" {
			http.Error(w, "Username not provided", http.StatusBadRequest)
			return
		}
	}

	// Initialize Redis client
	rdb := redis.NewClient(&redis.Options{
		Addr: "redis:6379", // Adjust the address if Redis is running elsewhere
	})

	// Retrieve the JWT token from Redis
	tokenKey := fmt.Sprintf("jwt_token_%s", username)
	token, err := rdb.Get(ctx, tokenKey).Result()
	if err == redis.Nil {
		// Get error with the username
		fmt.Println(username)
		http.Error(w, "JWT token not found for user", http.StatusUnauthorized)
		return
	} else if err != nil {
		http.Error(w, "Error retrieving JWT token", http.StatusInternalServerError)
		return
	}

	// Create a new request to the calendar service
	serviceURL := "http://calendar-service:5002"
	target := fmt.Sprintf("%s%s", serviceURL, r.RequestURI)
	req, err := http.NewRequest(r.Method, target, io.NopCloser(bytes.NewReader(bodyBytes)))
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Forward headers
	for k, v := range r.Header {
		req.Header.Set(k, v[0])
	}

	// Add the JWT token to the request headers
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token))

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

	respBody, _ := io.ReadAll(resp.Body)
	w.WriteHeader(resp.StatusCode)
	w.Write(respBody)
}
