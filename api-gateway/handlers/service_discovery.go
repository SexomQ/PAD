package handlers

import (
	"fmt"
	"net/http"

	"github.com/hashicorp/consul/api"
)

func GetServiceAddress(serviceName string) (string, error) {
	consulConfig := api.DefaultConfig()
	consulConfig.Address = "consul:8500"
	client, err := api.NewClient(consulConfig)
	if err != nil {
		return "", fmt.Errorf("failed to create Consul client: %v", err)
	}

	services, err := client.Agent().Services()
	if err != nil {
		return "", fmt.Errorf("failed to get services from Consul: %v", err)
	}

	for _, service := range services {
		if service.Service == serviceName {
			return fmt.Sprintf("http://%s:%d", service.Address, service.Port), nil
		}
	}
	return "", fmt.Errorf("service %s not found", serviceName)

}

func ServiceDiscoveryHandler(w http.ResponseWriter, r *http.Request) {
	consulConfig := api.DefaultConfig()
	consulConfig.Address = "consul:8500"
	_, err := api.NewClient(consulConfig)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(`{"status": "service discovery inactive"}`))
		return
	}
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "service discovery is up"}`))
}
