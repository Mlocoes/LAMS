package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"lams-agent/collector"
)

type HostRegister struct {
	ID            string  `json:"id"`
	Hostname      string  `json:"hostname"`
	IP            string  `json:"ip"`
	OS            string  `json:"os"`
	KernelVersion string  `json:"kernel_version"`
	CPUCores      int     `json:"cpu_cores"`
	TotalMemory   float64 `json:"total_memory"`
}

type MetricPayload struct {
	HostID           string  `json:"host_id"`
	Timestamp        string  `json:"timestamp"`
	CPUUsage         float64 `json:"cpu_usage"`
	LoadAverage      string  `json:"load_average"`
	MemoryUsed       float64 `json:"memory_used"`
	MemoryFree       float64 `json:"memory_free"`
	SwapUsed         float64 `json:"swap_used"`
	DiskTotal        float64 `json:"disk_total"`
	DiskUsed         float64 `json:"disk_used"`
	DiskUsagePercent float64 `json:"disk_usage_percent"`
	TemperatureCPU   float64 `json:"temp_cpu"`
	NetRx            float64 `json:"net_rx"`
	NetTx            float64 `json:"net_tx"`
}

type DockerSyncPayload struct {
	HostID     string                          `json:"host_id"`
	Containers []collector.DockerContainerData `json:"containers"`
}

type RemoteCommand struct {
	ID          int       `json:"id"`
	HostID      string    `json:"host_id"`
	CommandType string    `json:"command_type"`
	TargetID    string    `json:"target_id"`
	Status      string    `json:"status"`
	CreatedAt   string    `json:"created_at"`
	ExecutedAt  *string   `json:"executed_at"`
	Result      *string   `json:"result"`
}

type CommandResult struct {
	Status string `json:"status"`
	Result string `json:"result"`
}

func main() {
	serverURL := os.Getenv("LAMS_SERVER_URL")
	agentToken := os.Getenv("LAMS_AGENT_TOKEN")
	hostID := os.Getenv("LAMS_HOST_ID")

	if serverURL == "" {
		serverURL = "http://localhost:8000" // Default for local
	}
	if hostID == "" {
		hostID = "server01-dev"
	}

	log.Println("Starting LAMS Agent...")
	log.Printf("Target Server URL: %s", serverURL)
	if agentToken == "" {
		log.Println("WARNING: LAMS_AGENT_TOKEN is empty!")
	} else {
		log.Printf("Agent Token loaded: %s...%s (length: %d)", agentToken[:10], agentToken[len(agentToken)-10:], len(agentToken))
	}

	// Register Host
	registerHost(serverURL, agentToken, hostID)

	// Start command polling goroutine
	go func() {
		commandTicker := time.NewTicker(30 * time.Second)
		defer commandTicker.Stop()

		log.Println("Starting command polling (30s interval)...")

		for {
			<-commandTicker.C
			commands := pollCommands(serverURL, agentToken, hostID)

			for _, cmd := range commands {
				result := executeCommand(cmd)
				reportCommandResult(serverURL, agentToken, cmd.ID, result)
			}
		}
	}()

	// Main metrics collection loop
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for {
		<-ticker.C
		sysMetrics := collector.GetSystemMetrics()

		metrics := MetricPayload{
			HostID:           hostID,
			Timestamp:        time.Now().UTC().Format(time.RFC3339),
			CPUUsage:         sysMetrics.CPUUsage,
			LoadAverage:      sysMetrics.LoadAverage,
			MemoryUsed:       sysMetrics.MemoryUsed,
			MemoryFree:       sysMetrics.MemoryFree,
			SwapUsed:         sysMetrics.SwapUsed,
			DiskTotal:        sysMetrics.DiskTotal,
			DiskUsed:         sysMetrics.DiskUsed,
			DiskUsagePercent: sysMetrics.DiskUsagePercent,
			TemperatureCPU:   sysMetrics.TemperatureCPU,
			NetRx:            sysMetrics.NetRx,
			NetTx:            sysMetrics.NetTx,
		}

		sendMetrics(serverURL, agentToken, metrics)
		
		// Docker Sync
		dockerContainers := collector.GetDockerContainers()
		if len(dockerContainers) > 0 {
			syncDocker(serverURL, agentToken, hostID, dockerContainers)
		}
	}
}

func syncDocker(url, token, hostID string, containers []collector.DockerContainerData) {
	payload := DockerSyncPayload{
		HostID:     hostID,
		Containers: containers,
	}
	
	data, _ := json.Marshal(payload)
	req, _ := http.NewRequest("POST", fmt.Sprintf("%s/api/v1/docker/sync", url), bytes.NewBuffer(data))
	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("X-Agent-API-Key", token)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Error syncing docker: %v", err)
		return
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		log.Printf("Server returned status on docker sync: %d", resp.StatusCode)
	}
}

func registerHost(url, token, hostID string) {
	info := collector.GetHostInfo()
	
	// Mock IP for simplicity
	ip := "127.0.0.1" 
	
	reqData := HostRegister{
		ID:            hostID,
		Hostname:      info.Hostname,
		IP:            ip,
		OS:            info.OS,
		KernelVersion: info.KernelVersion,
		CPUCores:      info.CPUCores,
		TotalMemory:   info.TotalMemory,
	}

	data, _ := json.Marshal(reqData)
	req, _ := http.NewRequest("POST", fmt.Sprintf("%s/api/v1/hosts/register", url), bytes.NewBuffer(data))
	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("X-Agent-API-Key", token)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Failed to register host: %v", err)
		return
	}
	defer resp.Body.Close()
	
	if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusCreated {
		log.Println("Host successfully registered with Central Server.")
	} else {
		log.Printf("Failed to register host. Status code: %d", resp.StatusCode)
	}
}

func sendMetrics(url, token string, metrics MetricPayload) {
	log.Printf("DEBUG: Preparing to send metrics for host %s", metrics.HostID)
	
	data, err := json.Marshal(metrics)
	if err != nil {
		log.Printf("Error marshalling metrics: %v", err)
		return
	}

	req, err := http.NewRequest("POST", fmt.Sprintf("%s/api/v1/metrics/", url), bytes.NewBuffer(data))
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return
	}

	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("X-Agent-API-Key", token)
		log.Printf("DEBUG: Token set in header (length: %d)", len(token))
	} else {
		log.Printf("WARNING: Token is empty, not setting X-Agent-API-Key header")
	}

	log.Printf("DEBUG: Sending POST request to %s/api/v1/metrics/", url)
	
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Error sending metrics: %v", err)
		return
	}
	defer resp.Body.Close()

	log.Printf("DEBUG: Server responded with status code %d", resp.StatusCode)
	
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		log.Printf("Server returned status: %d, body: %s", resp.StatusCode, string(body))
	} else {
		log.Printf("✅ Metrics successfully sent for host %s", metrics.HostID)
	}
}

// pollCommands fetches pending commands from the server
func pollCommands(url, token, hostID string) []RemoteCommand {
	req, err := http.NewRequest("GET", fmt.Sprintf("%s/api/v1/commands/%s/pending", url, hostID), nil)
	if err != nil {
		log.Printf("Error creating poll request: %v", err)
		return nil
	}

	if token != "" {
		req.Header.Set("X-Agent-API-Key", token)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Error polling commands: %v", err)
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Server returned status on poll: %d", resp.StatusCode)
		return nil
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Error reading poll response: %v", err)
		return nil
	}

	var commands []RemoteCommand
	err = json.Unmarshal(body, &commands)
	if err != nil {
		log.Printf("Error unmarshalling commands: %v", err)
		return nil
	}

	return commands
}

// executeCommand executes a single remote command
func executeCommand(cmd RemoteCommand) CommandResult {
	var err error
	var result string

	log.Printf("Executing command: %s on target %s", cmd.CommandType, cmd.TargetID)

	switch cmd.CommandType {
	case "docker_start":
		err = collector.StartContainer(cmd.TargetID)
		if err == nil {
			result = fmt.Sprintf("Container %s started successfully", cmd.TargetID)
		}
	case "docker_stop":
		err = collector.StopContainer(cmd.TargetID)
		if err == nil {
			result = fmt.Sprintf("Container %s stopped successfully", cmd.TargetID)
		}
	case "docker_restart":
		err = collector.RestartContainer(cmd.TargetID)
		if err == nil {
			result = fmt.Sprintf("Container %s restarted successfully", cmd.TargetID)
		}
	default:
		err = fmt.Errorf("unknown command type: %s", cmd.CommandType)
	}

	if err != nil {
		return CommandResult{
			Status: "failed",
			Result: fmt.Sprintf("Error: %v", err),
		}
	}

	return CommandResult{
		Status: "completed",
		Result: result,
	}
}

// reportCommandResult reports the execution result back to the server
func reportCommandResult(url, token string, commandID int, result CommandResult) {
	data, err := json.Marshal(result)
	if err != nil {
		log.Printf("Error marshalling command result: %v", err)
		return
	}

	req, err := http.NewRequest("POST", fmt.Sprintf("%s/api/v1/commands/%d/result", url, commandID), bytes.NewBuffer(data))
	if err != nil {
		log.Printf("Error creating result request: %v", err)
		return
	}

	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("X-Agent-API-Key", token)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Error reporting result: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Server returned status on result report: %d", resp.StatusCode)
	} else {
		log.Printf("Command %d result reported successfully", commandID)
	}
}
