package handlers

import (
	"encoding/json"
	"net/http"
)

// StatusResponse represents the response structure for the status endpoint
type StatusResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
}

// StatusHandler is the handler for the status endpoint
func StatusHandler(w http.ResponseWriter, r *http.Request) {
	// Create a new StatusResponse
	response := StatusResponse{
		Status:  "OK",
		Message: "API Gateway is running",
	}

	// Convert the response to JSON
	responseJSON, err := json.Marshal(response)
	if err != nil {
		http.Error(w, "Failed to marshal JSON", http.StatusInternalServerError)
		return
	}

	// Write the response
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(responseJSON)
}
