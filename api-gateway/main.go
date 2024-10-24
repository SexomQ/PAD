package main

import (
	"gateway/handlers"
	"gateway/load_balancers"
	"gateway/middleware"
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

	// Start the server
	http.Handle("/", r)
	log.Println("Starting Gateway on port 8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
