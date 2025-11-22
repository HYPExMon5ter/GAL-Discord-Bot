#!/bin/bash
# Build the Next.js dashboard for production deployment

echo "🏗️  Building GAL Dashboard for production..."

cd dashboard

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Set production environment
export NODE_ENV=production

# Build the application
echo "🔨 Building Next.js application..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Dashboard build successful!"
    echo "📊 Production build ready at: dashboard/.next"
    echo "🚀 You can now deploy to Railway or run locally with npm start"
else
    echo "❌ Dashboard build failed!"
    exit 1
fi
