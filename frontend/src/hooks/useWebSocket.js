import { useState, useEffect, useRef, useCallback } from 'react'

export function useWebSocket() {
  const wsUrl = 'ws://localhost:5174/ws/realtime'
  const [sensorData, setSensorData] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const reconnectCountRef = useRef(0)
  const MAX_RECONNECT = 5

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)) {
      return
    }
    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws
      ws.onopen = () => {
        setIsConnected(true)
        reconnectCountRef.current = 0
      }
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setSensorData(data)
          setLastUpdated(new Date())
        } catch {}
      }
      ws.onclose = () => {
        setIsConnected(false)
        wsRef.current = null
        if (reconnectCountRef.current < MAX_RECONNECT) {
          const delay = Math.min(1000 * 2 ** reconnectCountRef.current, 30000)
          reconnectCountRef.current += 1
          reconnectTimerRef.current = setTimeout(connect, delay)
        }
      }
      ws.onerror = () => { ws.close() }
    } catch {
      setIsConnected(false)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  return { sensorData, isConnected, lastUpdated }
}