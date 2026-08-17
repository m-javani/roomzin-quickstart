package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

// ============================================================================
// CONFIGURATION
// ============================================================================

const (
	rzgateURL = "http://127.0.0.1:8777/api"
	timeout   = 30 * time.Second
)

// Test data parameters - matches smoke.go
const (
	numSegments        = 4
	numPropsPerSegment = 10
	numRoomsPerProp    = 4
	numDays            = 10
	shardIdx           = 1
)

// ============================================================================
// TYPES
// ============================================================================

type RzGateRequest struct {
	Command string                 `json:"command"`
	Segment string                 `json:"segment"`
	Body    map[string]interface{} `json:"body"`
}

type RzGateResponse struct {
	Status string                 `json:"status"`
	Data   map[string]interface{} `json:"data,omitempty"`
}

// ============================================================================
// HTTP CLIENT WITH RETRY
// ============================================================================

type RzGateClient struct {
	url    string
	client *http.Client
}

func NewRzGateClient(url string) *RzGateClient {
	return &RzGateClient{
		url: url,
		client: &http.Client{
			Timeout: timeout,
		},
	}
}

func (c *RzGateClient) Do(ctx context.Context, cmd, segment string, body map[string]interface{}) (*RzGateResponse, error) {
	req := RzGateRequest{
		Command: cmd,
		Segment: segment,
		Body:    body,
	}

	jsonData, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	// Retry logic
	maxRetries := 3
	var lastErr error

	for attempt := 0; attempt < maxRetries; attempt++ {
		if attempt > 0 {
			time.Sleep(100 * time.Millisecond)
			fmt.Printf("        Retry %d for %s\n", attempt+1, cmd)
		}

		httpReq, err := http.NewRequestWithContext(ctx, "POST", c.url, bytes.NewReader(jsonData))
		if err != nil {
			lastErr = err
			continue
		}
		httpReq.Header.Set("Content-Type", "application/json")

		resp, err := c.client.Do(httpReq)
		if err != nil {
			lastErr = err
			continue
		}
		defer resp.Body.Close()

		var result RzGateResponse
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			lastErr = err
			continue
		}

		return &result, nil
	}

	return nil, fmt.Errorf("failed after %d attempts: %v", maxRetries, lastErr)
}

// ============================================================================
// TIMING HELPERS
// ============================================================================

type StepTiming struct {
	name         string
	duration     time.Duration
	requestCount int
}

var timings []StepTiming

func timeStep(name string, requestCount int, fn func() error) error {
	start := time.Now()
	err := fn()
	duration := time.Since(start)

	timings = append(timings, StepTiming{
		name:         name,
		duration:     duration,
		requestCount: requestCount,
	})

	if err != nil {
		fmt.Printf("  ❌ %s failed after %v\n", name, duration)
	} else {
		fmt.Printf("  ✅ %s completed in %v (%d requests)\n", name, duration, requestCount)
	}
	return err
}

func printSummary() {
	fmt.Println("\n" + "=" + strings.Repeat("=", 60))
	fmt.Println("  RZGATE HTTP BENCHMARK SUMMARY")
	fmt.Println("=" + strings.Repeat("=", 60))

	var totalTime time.Duration
	var totalRequests int

	for _, t := range timings {
		totalTime += t.duration
		totalRequests += t.requestCount
		fmt.Printf("  %-25s %10v  %4d requests\n", t.name+":", t.duration, t.requestCount)
	}

	fmt.Println(strings.Repeat("-", 60))
	fmt.Printf("  %-25s %10v  %4d requests\n", "TOTAL:", totalTime, totalRequests)
	if totalRequests > 0 {
		fmt.Printf("  %-25s %10v\n", "Avg per request:", totalTime/time.Duration(totalRequests))
	}
	fmt.Println("=" + strings.Repeat("=", 60))
}

// ============================================================================
// TEST RZGATE HEALTH
// ============================================================================

func testRzGateHealth(url string) error {
	fmt.Println("Testing RzGate connection...")

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(strings.Replace(url, "/api", "/health", 1))
	if err != nil {
		return fmt.Errorf("health check failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("health check returned %d", resp.StatusCode)
	}

	fmt.Println("✅ RzGate is healthy")
	return nil
}

// ============================================================================
// MAIN
// ============================================================================

func main() {
	ctx := context.Background()
	client := NewRzGateClient(rzgateURL)

	fmt.Println("=== RzGate HTTP Benchmark ===")
	fmt.Printf("URL: %s\n\n", rzgateURL)

	// Check if RzGate is running
	if err := testRzGateHealth(rzgateURL); err != nil {
		log.Fatalf("RzGate not available: %v", err)
	}

	// -------------------------------------------------------------------------
	// STEP 1: SetProp
	// -------------------------------------------------------------------------
	fmt.Println("\n[1/6] SetProp...")

	err := timeStep("SetProp", numSegments*numPropsPerSegment, func() error {
		for s := 1; s <= numSegments; s++ {
			segment := fmt.Sprintf("segment_%d", s)

			for p := 1; p <= numPropsPerSegment; p++ {
				propID := fmt.Sprintf("s%d_seg%d_p%d", shardIdx, s, p)

				body := map[string]interface{}{
					"segment":       segment,
					"area":          fmt.Sprintf("area_%d_%d", shardIdx, s),
					"property_id":   propID,
					"property_type": "hotel",
					"category":      "midrange",
					"stars":         3,
					"latitude":      40.7128 + float64(p)*0.001,
					"longitude":     -74.0060 + float64(p)*0.001,
					"amenities":     []string{"wifi", "pool"},
				}

				fmt.Printf("        Creating %s...\n", propID)
				_, err := client.Do(ctx, "SETPROP", segment, body)
				if err != nil {
					return fmt.Errorf("SETPROP %s failed: %v", propID, err)
				}
			}
		}
		return nil
	})
	if err != nil {
		log.Fatalf("SetProp failed: %v", err)
	}

	// -------------------------------------------------------------------------
	// STEP 2: SetRoomPkg
	// -------------------------------------------------------------------------
	fmt.Println("\n[2/6] SetRoomPkg...")

	err = timeStep("SetRoomPkg", numSegments*numPropsPerSegment*numRoomsPerProp*numDays, func() error {
		// Generate dates
		dates := make([]string, numDays)
		for i := range numDays {
			date := time.Now().Add(time.Duration(i) * 24 * time.Hour)
			dates[i] = date.Format("2006-01-02")
		}

		for s := 1; s <= numSegments; s++ {
			segment := fmt.Sprintf("segment_%d", s)

			for p := 1; p <= numPropsPerSegment; p++ {
				propID := fmt.Sprintf("s%d_seg%d_p%d", shardIdx, s, p)

				for r := 1; r <= numRoomsPerProp; r++ {
					roomType := fmt.Sprintf("room%d", r)

					for _, date := range dates {
						body := map[string]interface{}{
							"property_id":   propID,
							"room_type":     roomType,
							"date":          date,
							"availability":  10 + p,
							"final_price":   100 + p*10,
							"rate_features": []string{"free_cancellation", "free_wifi"},
						}

						_, err := client.Do(ctx, "SETROOMPKG", segment, body)
						if err != nil {
							return fmt.Errorf("SETROOMPKG %s/%s/%s failed: %v", propID, roomType, date, err)
						}
					}
				}
			}
		}
		return nil
	})
	if err != nil {
		log.Fatalf("SetRoomPkg failed: %v", err)
	}

	// -------------------------------------------------------------------------
	// STEP 3: GetPropRoomDay (spot check)
	// -------------------------------------------------------------------------
	fmt.Println("\n[3/6] GetPropRoomDay...")

	err = timeStep("GetPropRoomDay", 1, func() error {
		testProp := fmt.Sprintf("s%d_seg1_p1", shardIdx)
		roomType := "room1"
		date := time.Now().Format("2006-01-02")

		body := map[string]interface{}{
			"property_id": testProp,
			"room_type":   roomType,
			"date":        date,
		}

		resp, err := client.Do(ctx, "GETPROPROOMDAY", "segment_1", body)
		if err != nil {
			return err
		}

		if resp.Status != "success" {
			return fmt.Errorf("GETPROPROOMDAY failed: %+v", resp)
		}
		return nil
	})
	if err != nil {
		log.Fatalf("GetPropRoomDay failed: %v", err)
	}

	// -------------------------------------------------------------------------
	// STEP 4: SearchAvail
	// -------------------------------------------------------------------------
	fmt.Println("\n[4/6] SearchAvail...")

	err = timeStep("SearchAvail", 1, func() error {
		date := time.Now().Format("2006-01-02")
		limit := uint64(100)
		maxPrice := uint32(150)

		body := map[string]interface{}{
			"segment":     "segment_1",
			"room_type":   "room1",
			"date":        []string{date},
			"final_price": maxPrice,
			"limit":       limit,
		}

		resp, err := client.Do(ctx, "SEARCHAVAIL", "segment_1", body)
		if err != nil {
			return err
		}

		if resp.Status != "success" {
			return fmt.Errorf("SEARCHAVAIL failed: %+v", resp)
		}
		return nil
	})
	if err != nil {
		log.Fatalf("SearchAvail failed: %v", err)
	}

	// -------------------------------------------------------------------------
	// STEP 5: Update Availability (Set, Inc, Dec)
	// -------------------------------------------------------------------------
	fmt.Println("\n[5/6] Update Availability...")

	err = timeStep("Update Availability", 3, func() error {
		testProp := fmt.Sprintf("s%d_seg1_p1", shardIdx)
		roomType := "room1"
		date := time.Now().Format("2006-01-02")

		// Set
		body := map[string]interface{}{
			"property_id": testProp,
			"room_type":   roomType,
			"date":        date,
			"amount":      20,
		}
		resp, err := client.Do(ctx, "SETROOMAVL", "segment_1", body)
		if err != nil {
			return err
		}
		if resp.Status != "success" {
			return fmt.Errorf("SETROOMAVL failed: %+v", resp)
		}

		// Inc
		body = map[string]interface{}{
			"property_id": testProp,
			"room_type":   roomType,
			"date":        date,
			"amount":      1,
		}
		resp, err = client.Do(ctx, "INCROOMAVL", "segment_1", body)
		if err != nil {
			return err
		}
		if resp.Status != "success" {
			return fmt.Errorf("INCROOMAVL failed: %+v", resp)
		}

		// Dec
		resp, err = client.Do(ctx, "DECROOMAVL", "segment_1", body)
		if err != nil {
			return err
		}
		if resp.Status != "success" {
			return fmt.Errorf("DECROOMAVL failed: %+v", resp)
		}

		return nil
	})
	if err != nil {
		log.Fatalf("Update Availability failed: %v", err)
	}

	// -------------------------------------------------------------------------
	// STEP 6: Cleanup
	// -------------------------------------------------------------------------
	fmt.Println("\n[6/6] Cleanup...")

	err = timeStep("Cleanup", numSegments, func() error {
		for s := 1; s <= numSegments; s++ {
			seg := fmt.Sprintf("segment_%d", s)
			body := map[string]interface{}{
				"segment": seg,
			}
			_, err := client.Do(ctx, "DELSEGMENT", seg, body)
			if err != nil {
				fmt.Printf("        Warning: Failed to delete %s: %v\n", seg, err)
			} else {
				fmt.Printf("        Cleaned up %s\n", seg)
			}
		}
		return nil
	})
	if err != nil {
		log.Printf("Cleanup had issues: %v", err)
	}

	// -------------------------------------------------------------------------
	// SUMMARY
	// -------------------------------------------------------------------------
	printSummary()
	fmt.Println("\n✅ All completed successfully!")
}
