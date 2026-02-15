// Package main: HTTP request/response models compatible with ADK REST session API.
package main

import (
	"fmt"
	"maps"
	"time"

	"github.com/mitchellh/mapstructure"
	"google.golang.org/adk/model"
	"google.golang.org/adk/session"
	"google.golang.org/genai"
)

// Session is the REST JSON shape for a session (ADK compatible).
type Session struct {
	ID             string         `json:"id"`
	AppName        string         `json:"appName"`
	UserID         string         `json:"userId"`
	LastUpdateTime int64          `json:"lastUpdateTime"`
	Events         []Event        `json:"events"`
	State          map[string]any `json:"state"`
}

// CreateSessionRequest is the REST body for creating a session.
type CreateSessionRequest struct {
	State  map[string]any `json:"state"`
	Events []Event        `json:"events"`
}

// Event is the REST JSON shape for a session event (ADK compatible).
type Event struct {
	ID                 string                   `json:"id"`
	Time               int64                    `json:"time"`
	InvocationID       string                   `json:"invocationId"`
	Branch             string                   `json:"branch"`
	Author             string                   `json:"author"`
	Partial            bool                     `json:"partial"`
	LongRunningToolIDs []string                 `json:"longRunningToolIds"`
	Content            *genai.Content            `json:"content"`
	GroundingMetadata  *genai.GroundingMetadata  `json:"groundingMetadata"`
	TurnComplete       bool                     `json:"turnComplete"`
	Interrupted        bool                     `json:"interrupted"`
	ErrorCode          string                   `json:"errorCode"`
	ErrorMessage       string                   `json:"errorMessage"`
	Actions            EventActions             `json:"actions"`
}

// EventActions is the REST shape for event actions.
type EventActions struct {
	StateDelta    map[string]any   `json:"stateDelta"`
	ArtifactDelta map[string]int64 `json:"artifactDelta"`
}

// SessionID holds app_name, user_id, session_id from path.
type SessionID struct {
	ID      string `mapstructure:"session_id,optional"`
	AppName string `mapstructure:"app_name,required"`
	UserID  string `mapstructure:"user_id,required"`
}

// SessionIDFromVars decodes path variables into SessionID.
func SessionIDFromVars(vars map[string]string) (SessionID, error) {
	var sid SessionID
	decoder, err := mapstructure.NewDecoder(&mapstructure.DecoderConfig{
		WeaklyTypedInput: true,
		Result:           &sid,
		TagName:          "mapstructure",
	})
	if err != nil {
		return sid, err
	}
	if err := decoder.Decode(vars); err != nil {
		return sid, err
	}
	if sid.AppName == "" {
		return sid, fmt.Errorf("app_name parameter is required")
	}
	if sid.UserID == "" {
		return sid, fmt.Errorf("user_id parameter is required")
	}
	return sid, nil
}

// FromSession converts session.Session to REST Session.
func FromSession(s session.Session) (Session, error) {
	state := map[string]any{}
	maps.Copy(state, sessionStateAll(s.State()))
	events := []Event{}
	for e := range s.Events().All() {
		events = append(events, FromSessionEvent(*e))
	}
	return Session{
		ID:             s.ID(),
		AppName:        s.AppName(),
		UserID:         s.UserID(),
		LastUpdateTime: s.LastUpdateTime().Unix(),
		Events:         events,
		State:          state,
	}, nil
}

func sessionStateAll(st session.State) map[string]any {
	m := make(map[string]any)
	for k, v := range st.All() {
		m[k] = v
	}
	return m
}

// FromSessionEvent converts session.Event to REST Event.
func FromSessionEvent(e session.Event) Event {
	actions := EventActions{}
	if e.Actions.StateDelta != nil {
		actions.StateDelta = e.Actions.StateDelta
	}
	if e.Actions.ArtifactDelta != nil {
		actions.ArtifactDelta = e.Actions.ArtifactDelta
	}
	return Event{
		ID:                 e.ID,
		Time:               e.Timestamp.Unix(),
		InvocationID:       e.InvocationID,
		Branch:             e.Branch,
		Author:             e.Author,
		Partial:            e.Partial,
		LongRunningToolIDs: e.LongRunningToolIDs,
		Content:            e.Content,
		GroundingMetadata:  e.GroundingMetadata,
		TurnComplete:       e.TurnComplete,
		Interrupted:        e.Interrupted,
		ErrorCode:          e.ErrorCode,
		ErrorMessage:       e.ErrorMessage,
		Actions:            actions,
	}
}

// ToSessionEvent converts REST Event to session.Event.
func ToSessionEvent(e Event) *session.Event {
	return &session.Event{
		ID:                 e.ID,
		Timestamp:          time.Unix(e.Time, 0),
		InvocationID:       e.InvocationID,
		Branch:             e.Branch,
		Author:             e.Author,
		LongRunningToolIDs: e.LongRunningToolIDs,
		LLMResponse: model.LLMResponse{
			Content:           e.Content,
			GroundingMetadata: e.GroundingMetadata,
			Partial:           e.Partial,
			TurnComplete:      e.TurnComplete,
			Interrupted:       e.Interrupted,
			ErrorCode:         e.ErrorCode,
			ErrorMessage:     e.ErrorMessage,
		},
		Actions: session.EventActions{
			StateDelta:    e.Actions.StateDelta,
			ArtifactDelta: e.Actions.ArtifactDelta,
		},
	}
}
