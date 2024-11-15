package load_balancers

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/hashicorp/consul/api"
	"golang.org/x/exp/rand"
)

var (
	mu         sync.Mutex
	serviceId  = map[string]string{}
	loginIndex int
	// userServiceBreaker  = middleware.NewCircuitBreaker(3, 30*time.Second) // Set limit and timeout
	// classServiceBreaker = middleware.NewCircuitBreaker(3, 5*time.Second)  // Set limit and timeout
)

// variable to store the instances of the services
var serviceCache = map[string][]string{"user-management-service": {}, "calendar-service": {}}

var loadTracking = map[string][]int{"user-management-service": {}, "calendar-service": {}}

// update the serviceCache with the instances of the services
func UpdateServiceCache(serviceName string) {
	mu.Lock()
	defer mu.Unlock()

	consulConfig := api.DefaultConfig()
	consulConfig.Address = "consul:8500"

	_, err := api.NewClient(consulConfig)
	if err != nil {
		log.Println("Failed to create Consul client")
		return
	}

	healthCheckUrl := fmt.Sprintf("http://%s/v1/health/service/%s", consulConfig.Address, serviceName)
	resp, err := http.Get(healthCheckUrl)
	if err != nil {
		log.Printf("Failed to get service health status for %s : %v", serviceName, err)
		return
	}
	defer resp.Body.Close()

	// read and parse the response body
	healthStatus, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Failed to read response body for %s", serviceName)
		return
	}

	var healthData []api.ServiceEntry
	if err := json.Unmarshal(healthStatus, &healthData); err != nil {
		log.Printf("Failed to parse health check response: %v", err)
		return
	}
	// remove the unhealthy instances
	var healthyServices []string
	var unhealthyServices []string
	for _, entry := range healthData {
		isHealthy := true
		for _, check := range entry.Checks {
			if check.Status != "passing" {
				isHealthy = false
				break
			}
		}

		serviceUrl := fmt.Sprintf("http://%s:%d", entry.Service.Address, entry.Service.Port)
		serviceIdValue := entry.Service.ID

		if isHealthy {
			healthyServices = append(healthyServices, serviceUrl)
			serviceId[serviceUrl] = serviceIdValue
		} else {
			unhealthyServices = append(unhealthyServices, serviceUrl)
		}
	}

	// Update service cache with healthy services
	serviceCache[serviceName] = healthyServices

	// Initialize load tracking for healthy services
	if len(loadTracking[serviceName]) == 0 {
		loadTracking[serviceName] = make([]int, len(healthyServices))

		// Randomly set load values for testing purposes
		for i := range healthyServices {
			loadTracking[serviceName][i] = rand.Intn(100)
		}
	}

	// Print the service cache
	log.Printf("Service cache updated for %s: %v", serviceName, serviceCache[serviceName])
	fmt.Printf("Load Tracking: %v\n", loadTracking[serviceName])
}

// load balancers
func RoundRobinLoadBalancer(serviceName string) string {
	mu.Lock()
	defer mu.Unlock()
	if len(serviceCache[serviceName]) == 0 {
		return ""
	}
	serviceUrl := serviceCache[serviceName][loginIndex]
	loginIndex = (loginIndex + 1) % len(serviceCache[serviceName])
	fmt.Printf("This is the service url DE LA ROBIN %s \n", serviceUrl)
	return serviceUrl
}

func PeriodicallyUpdateServiceCache() {
	for {
		UpdateServiceCache("user-management-service")
		UpdateServiceCache("calendar-service")
		// time.Sleep(10 * time.Second)
		time.Sleep(30 * time.Second)
	}
}
