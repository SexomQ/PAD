package main

import (
	"gateway/handlers"
	"gateway/middleware"
	"log"
	"net/http"

	"github.com/gorilla/mux"
)

func main() {

	// Initialize Redis
	middleware.InitRedis()

	// Create a new router
	r := mux.NewRouter()

	// User-related routes
	r.PathPrefix("/api/user/").HandlerFunc(handlers.UserHandler)

	// Calendar-related routes
	r.PathPrefix("/api/calendar/").HandlerFunc(handlers.CalendarHandler)

	// Check all records in Redis
	r.HandleFunc("/api/redis", middleware.CheckRedis)

	// Start the server
	http.Handle("/", r)
	log.Println("Starting Gateway on port 8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
