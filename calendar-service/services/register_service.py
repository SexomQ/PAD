import consul
import socket

def register_service():
    consul_client = consul.Consul(host='consul', port=8500)

    service_address = socket.gethostbyname(socket.gethostname())
    service_id = f'calendar_service-{service_address}'
    service_name = 'calendar_service'
    service_port = 5002

    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=service_address,
        port=service_port,
        tags=['calendar'],
        check=consul.Check.http(f'http://{service_address}:{service_port}/api/calendar/status',
                                 interval='30s')
    )

if __name__ == "__main__":
    register_service()