#!/bin/bash
# VoteChain V3 - Master Control Script

case "$1" in
    start)
        echo "🚀 Starting all VoteChain services..."
        sudo systemctl start votechain votechain-frontend votechain-kiosk
        sleep 3
        ./check-system.sh
        ;;
    stop)
        echo "🛑 Stopping all VoteChain services..."
        sudo systemctl stop votechain votechain-frontend votechain-kiosk
        echo "✅ All services stopped"
        ;;
    restart)
        echo "🔄 Restarting all VoteChain services..."
        sudo systemctl restart votechain votechain-frontend votechain-kiosk
        sleep 3
        ./check-system.sh
        ;;
    status)
        ./check-system.sh
        ;;
    logs)
        if [ -z "$2" ]; then
            echo "Usage: $0 logs [backend|frontend|kiosk]"
            exit 1
        fi
        case "$2" in
            backend)
                tail -f /home/cainepi/votechain-backend.log
                ;;
            frontend)
                tail -f /home/cainepi/votechain-frontend.log
                ;;
            kiosk)
                tail -f /home/cainepi/votechain-kiosk.log
                ;;
            *)
                echo "Unknown service: $2"
                echo "Available: backend, frontend, kiosk"
                ;;
        esac
        ;;
    enable)
        echo "✅ Enabling auto-start on boot..."
        sudo systemctl enable votechain votechain-frontend votechain-kiosk
        echo "✅ Services will start automatically on boot"
        ;;
    disable)
        echo "❌ Disabling auto-start on boot..."
        sudo systemctl disable votechain votechain-frontend votechain-kiosk
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
