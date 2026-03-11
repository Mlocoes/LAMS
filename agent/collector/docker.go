package collector

import (
	"context"
	"encoding/json"
	"io"
	"log"
	"net"
	"net/http"
	"time"
)

type DockerContainerData struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Image       string    `json:"image"`
	State       string    `json:"state"`
	CPUPercent  float64   `json:"cpu_percent"`
	MemoryUsage float64   `json:"memory_usage"`
	CreatedAt   time.Time `json:"created_at"`
}

type dockerContainerJSON struct {
	Id      string   `json:"Id"`
	Names   []string `json:"Names"`
	Image   string   `json:"Image"`
	State   string   `json:"State"`
	Created int64    `json:"Created"`
}

func getDockerClient() *http.Client {
	return &http.Client{
		Transport: &http.Transport{
			DialContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
				return net.Dial("unix", "/var/run/docker.sock")
			},
		},
		Timeout: 5 * time.Second,
	}
}

// GetDockerContainers returns a list of containers if docker is running
func GetDockerContainers() []DockerContainerData {
	client := getDockerClient()

	resp, err := client.Get("http://localhost/containers/json?all=true")
	if err != nil {
		// Docker is likely not installed or agent doesn't have permissions
		return nil
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Error reading docker response: %v", err)
		return nil
	}

	var containers []dockerContainerJSON
	err = json.Unmarshal(body, &containers)
	if err != nil {
		log.Printf("Error unmarshalling docker output: %v", err)
		return nil
	}

	var result []DockerContainerData
	for _, c := range containers {
		name := ""
		if len(c.Names) > 0 {
			name = c.Names[0][1:] // Remove leading slash
		}

		result = append(result, DockerContainerData{
			ID:          c.Id[:12],
			Name:        name,
			Image:       c.Image,
			State:       c.State,
			CPUPercent:  0.0, // Collecting precise docker stats takes more requests. Keeping it at 0 for speed initially.
			MemoryUsage: 0.0,
			CreatedAt:   time.Unix(c.Created, 0).UTC(),
		})
	}
	return result
}

// StartContainer starts a Docker container by ID
func StartContainer(containerID string) error {
	client := getDockerClient()
	
	req, err := http.NewRequest("POST", "http://localhost/containers/"+containerID+"/start", nil)
	if err != nil {
		return err
	}
	
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusNoContent && resp.StatusCode != http.StatusNotModified {
		body, _ := io.ReadAll(resp.Body)
		log.Printf("Docker start failed with status %d: %s", resp.StatusCode, string(body))
		return http.ErrAbortHandler
	}
	
	return nil
}

// StopContainer stops a Docker container by ID
func StopContainer(containerID string) error {
	client := getDockerClient()
	
	req, err := http.NewRequest("POST", "http://localhost/containers/"+containerID+"/stop", nil)
	if err != nil {
		return err
	}
	
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusNoContent && resp.StatusCode != http.StatusNotModified {
		body, _ := io.ReadAll(resp.Body)
		log.Printf("Docker stop failed with status %d: %s", resp.StatusCode, string(body))
		return http.ErrAbortHandler
	}
	
	return nil
}

// RestartContainer restarts a Docker container by ID
func RestartContainer(containerID string) error {
	client := getDockerClient()
	
	req, err := http.NewRequest("POST", "http://localhost/containers/"+containerID+"/restart", nil)
	if err != nil {
		return err
	}
	
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusNoContent {
		body, _ := io.ReadAll(resp.Body)
		log.Printf("Docker restart failed with status %d: %s", resp.StatusCode, string(body))
		return http.ErrAbortHandler
	}
	
	return nil
}
