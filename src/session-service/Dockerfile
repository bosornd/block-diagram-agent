# Build stage
FROM golang:1.24-alpine AS builder
WORKDIR /build

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o session-service .

# Run stage
FROM alpine:3.20
RUN apk --no-cache add ca-certificates
WORKDIR /app

COPY --from=builder /build/session-service .

EXPOSE 8081
ENV PORT=8081

ENTRYPOINT ["/app/session-service"]
