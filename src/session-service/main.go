package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
	"google.golang.org/adk/session/database"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func buildDSN() string {
	if dsn := os.Getenv("SESSION_DATABASE_URL"); dsn != "" {
		return dsn
	}
	host := os.Getenv("SESSION_DB_HOST")
	user := os.Getenv("SESSION_DB_USER")
	password := os.Getenv("SESSION_DB_PASSWORD")
	dbname := os.Getenv("SESSION_DB_NAME")
	if host == "" || user == "" || password == "" || dbname == "" {
		return ""
	}
	port := os.Getenv("SESSION_DB_PORT")
	if port == "" {
		port = "5432"
	}
	sslmode := os.Getenv("SESSION_DB_SSLMODE")
	if sslmode == "" {
		sslmode = "disable"
	}
	return fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=%s",
		host, user, password, dbname, port, sslmode)
}

func main() {
	dsn := buildDSN()
	if dsn == "" {
		log.Fatal("session DB required: set SESSION_DATABASE_URL or SESSION_DB_* env vars")
	}
	svc, err := database.NewSessionService(postgres.Open(dsn))
	if err != nil {
		log.Fatalf("Failed to create session service: %v", err)
	}
	if err := database.AutoMigrate(svc); err != nil {
		log.Fatalf("Failed to migrate session DB: %v", err)
	}
	// 세션 삭제 시 FK 제약(events) 회피를 위해 동일 DB 연결 사용
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		log.Fatalf("Failed to open DB for delete: %v", err)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}

	r := mux.NewRouter()
	r.HandleFunc("/", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK) }).Methods(http.MethodGet)
	r.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK) }).Methods(http.MethodGet)
	api := r.PathPrefix("/api").Subrouter()

	// ADK-compatible session routes (same paths as ADK REST)
	api.HandleFunc("/apps/{app_name}/users/{user_id}/sessions", listSessionsHandler(svc)).Methods(http.MethodGet)
	api.HandleFunc("/apps/{app_name}/users/{user_id}/sessions", createSessionHandler(svc)).Methods(http.MethodPost)
	api.HandleFunc("/apps/{app_name}/users/{user_id}/sessions/{session_id}", getSessionHandler(svc)).Methods(http.MethodGet)
	api.HandleFunc("/apps/{app_name}/users/{user_id}/sessions/{session_id}", createSessionHandler(svc)).Methods(http.MethodPost)
	api.HandleFunc("/apps/{app_name}/users/{user_id}/sessions/{session_id}", deleteSessionHandler(svc, db)).Methods(http.MethodDelete)
	// Append event (used by agent's remote session client)
	api.HandleFunc("/apps/{app_name}/users/{user_id}/sessions/{session_id}/events", appendEventHandler(svc)).Methods(http.MethodPost)

	http.Handle("/", cors(r))
	log.Printf("Session service listening on :%s", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

func cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}
		next.ServeHTTP(w, r)
	})
}
