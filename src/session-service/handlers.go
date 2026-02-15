package main

import (
	"encoding/json"
	"net/http"

	"github.com/gorilla/mux"
	"google.golang.org/adk/session"
	"gorm.io/gorm"
)

func listSessionsHandler(svc session.Service) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		sid, err := SessionIDFromVars(mux.Vars(r))
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		resp, err := svc.List(r.Context(), &session.ListRequest{
			AppName: sid.AppName,
			UserID:  sid.UserID,
		})
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		out := make([]Session, 0, len(resp.Sessions))
		for _, s := range resp.Sessions {
			sess, err := FromSession(s)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			out = append(out, sess)
		}
		writeJSON(w, http.StatusOK, out)
	}
}

func createSessionHandler(svc session.Service) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		sid, err := SessionIDFromVars(mux.Vars(r))
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		var req CreateSessionRequest
		if r.ContentLength > 0 {
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
		}
		if req.State == nil {
			req.State = map[string]any{}
		}
		createResp, err := svc.Create(r.Context(), &session.CreateRequest{
			AppName:   sid.AppName,
			UserID:    sid.UserID,
			SessionID: sid.ID,
			State:     req.State,
		})
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		for _, e := range req.Events {
			if err := svc.AppendEvent(r.Context(), createResp.Session, ToSessionEvent(e)); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
		}
		// Re-get to include events if any
		getResp, err := svc.Get(r.Context(), &session.GetRequest{
			AppName:   sid.AppName,
			UserID:    sid.UserID,
			SessionID: createResp.Session.ID(),
		})
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		sess, err := FromSession(getResp.Session)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		writeJSON(w, http.StatusOK, sess)
	}
}

func getSessionHandler(svc session.Service) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		sid, err := SessionIDFromVars(mux.Vars(r))
		if err != nil || sid.ID == "" {
			http.Error(w, "session_id parameter is required", http.StatusBadRequest)
			return
		}
		resp, err := svc.Get(r.Context(), &session.GetRequest{
			AppName:   sid.AppName,
			UserID:    sid.UserID,
			SessionID: sid.ID,
		})
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		sess, err := FromSession(resp.Session)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		writeJSON(w, http.StatusOK, sess)
	}
}

func deleteSessionHandler(svc session.Service, db *gorm.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		sid, err := SessionIDFromVars(mux.Vars(r))
		if err != nil || sid.ID == "" {
			http.Error(w, "session_id parameter is required", http.StatusBadRequest)
			return
		}
		// ADK sessions 테이블과 events 테이블에 FK가 있어 세션만 삭제하면 실패할 수 있음. events를 먼저 삭제.
		if db != nil {
			if res := db.Exec("DELETE FROM events WHERE app_name = ? AND user_id = ? AND session_id = ?",
				sid.AppName, sid.UserID, sid.ID); res.Error != nil {
				http.Error(w, res.Error.Error(), http.StatusInternalServerError)
				return
			}
		}
		if err := svc.Delete(r.Context(), &session.DeleteRequest{
			AppName:   sid.AppName,
			UserID:    sid.UserID,
			SessionID: sid.ID,
		}); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		writeJSON(w, http.StatusOK, nil)
	}
}

// appendEventHandler handles POST .../sessions/{id}/events for agent's remote session client.
func appendEventHandler(svc session.Service) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		sid, err := SessionIDFromVars(mux.Vars(r))
		if err != nil || sid.ID == "" {
			http.Error(w, "session_id parameter is required", http.StatusBadRequest)
			return
		}
		var ev Event
		if err := json.NewDecoder(r.Body).Decode(&ev); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		getResp, err := svc.Get(r.Context(), &session.GetRequest{
			AppName:   sid.AppName,
			UserID:    sid.UserID,
			SessionID: sid.ID,
		})
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		if err := svc.AppendEvent(r.Context(), getResp.Session, ToSessionEvent(ev)); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if v != nil {
		_ = json.NewEncoder(w).Encode(v)
	}
}
