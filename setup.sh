#!/bin/bash

# ServiceNow MCP Server Setup Script

echo "========================================="
echo "ServiceNow MCP Server Configuration"
echo "========================================="
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  A .env file already exists."
    read -p "Do you want to overwrite it? (y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Collect ServiceNow instance details
echo "Please provide your ServiceNow instance details:"
echo ""

read -p "ServiceNow Instance (e.g., dev12345 or dev12345.service-now.com): " instance
read -p "ServiceNow Username: " username
read -sp "ServiceNow Password: " password
echo ""

# Create .env file
cat > .env << EOF
# ServiceNow Instance Configuration
SERVICENOW_INSTANCE=$instance

# ServiceNow Basic Authentication
SERVICENOW_USERNAME=$username
SERVICENOW_PASSWORD=$password
EOF

echo ""
echo "✅ Configuration saved to .env"
echo ""
echo "Next steps:"
echo "1. Restart Claude Code to load the MCP server"
echo "2. The ServiceNow tools will be available in your Claude conversations"
echo ""
echo "To test the connection, you can try asking Claude:"
echo '  "Can you query the incident table in ServiceNow?"'
echo ""
