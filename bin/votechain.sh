#!/bin/bash
# VoteChain V3 - Master Control Script

case "$1" in
    start)
        echo "🚀 Starting all VoteChain services..."
        sudo systemctl start votechain-backend votechain-tunnel votechain-kiosk
        sleep 3
        ./check-system.sh
        ;;
    stop)
        echo "🛑 Stopping all VoteChain services..."
        sudo systemctl stop votechain-backend votechain-tunnel votechain-kiosk
        echo "✅ All services stopped"
        ;;
    restart)
        echo "🔄 Restarting all VoteChain services..."
        sudo systemctl restart votechain-backend votechain-tunnel votechain-kiosk
        sleep 3
        ./check-system.sh
        ;;
    status)
        ./check-system.sh
        ;;
    logs)
        if [ -z "$2" ]; then
            echo "Usage: $0 logs [backend|tunnel|kiosk]"
            exit 1
        fi
        case "$2" in
            backend)
                sudo journalctl -u votechain-backend -f
                ;;
            tunnel)
                sudo journalctl -u votechain-tunnel -f
                ;;
            kiosk)
                sudo journalctl -u votechain-kiosk -f
                ;;
            *)
                echo "Unknown service: $2"
                echo "Available: backend, tunnel, kiosk"
                ;;
        esac
        ;;
    enable)
        echo "✅ Enabling auto-start on boot..."
        sudo systemctl enable votechain-backend votechain-tunnel votechain-kiosk
        echo "✅ Services will start automatically on boot"
        ;;
    disable)
        echo "❌ Disabling auto-start on boot..."
        sudo systemctl disable votechain-backend votechain-tunnel votechain-kiosk
        echo "✅ Auto-start disabled"
        ;;
    *)
        echo "VoteChain V3 - Master Control"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable}"
        echo ""
        echo "Commands:"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Check system status"
        echo "  logs      - View logs (backend|frontend|kiosk)"
        echo "  enable    - Enable auto-start on boot"
        echo "  disable   - Disable auto-start on boot"
        echo ""
        exit 1
        ;;
esac
