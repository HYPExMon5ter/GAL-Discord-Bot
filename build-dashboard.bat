@echo off
REM Build the Next.js dashboard for production deployment (Windows)

echo 🏗️  Building GAL Dashboard for production...

cd dashboard

REM Check if node_modules exists
if not exist "node_modules" (
    echo 📦 Installing dependencies...
    npm install
)

REM Set production environment
set NODE_ENV=production

REM Build the application
echo 🔨 Building Next.js application...
npm run build

if %ERRORLEVEL% EQU 0 (
    echo ✅ Dashboard build successful!
    echo 📊 Production build ready at: dashboard\.next
    echo 🚀 You can now deploy to Railway or run locally with npm start
) else (
    echo ❌ Dashboard build failed!
    exit /b 1
)

cd ..
