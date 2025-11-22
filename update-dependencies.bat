@echo off
REM Update dashboard dependencies and fix security issues (Windows)

echo 🔒 Updating GAL Dashboard dependencies for security...

cd dashboard

REM Update to latest secure versions
echo 📦 Installing latest secure package versions...
npm update next eslint-config-next js-yaml

REM Fix remaining vulnerabilities (safe for development deps)
echo 🛠️  Fixing remaining security vulnerabilities...
npm audit fix --force

REM Clean up
npm cache clean --force

echo ✅ Dependencies updated successfully!
echo 📊 Summary:
npm audit
echo.
echo 🚀 You can now build and deploy with improved security

cd ..
