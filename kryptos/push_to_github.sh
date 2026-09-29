#!/usr/bin/env bash
set -e

# Kryptos & Paradigm Kryptos GitHub Push Script
# Usage:
#   ./push_to_github.sh <GITHUB_REPO_URL_OR_USER/REPO> [GITHUB_TOKEN]
# Example:
#   ./push_to_github.sh 0xdiid/kryptos-suite
#   ./push_to_github.sh https://github.com/0xdiid/kryptos-suite.git
#   ./push_to_github.sh 0xdiid/kryptos-suite ghp_xxxxxxxxxxxxxx

TARGET="$1"
TOKEN="$2"

if [ -z "$TARGET" ]; then
    echo "================================================================="
    echo "  Kryptos Master Suite — GitHub Remote Push Utility"
    echo "================================================================="
    echo "Usage:"
    echo "  ./push_to_github.sh <USER/REPO_OR_URL> [TOKEN]"
    echo ""
    echo "Examples:"
    echo "  ./push_to_github.sh 0xdiid/kryptos-suite"
    echo "  ./push_to_github.sh https://github.com/0xdiid/kryptos-suite.git"
    echo "  ./push_to_github.sh 0xdiid/kryptos-suite ghp_YourTokenHere"
    echo "================================================================="
    exit 1
fi

# Format URL
if [[ "$TARGET" =~ ^https:// || "$TARGET" =~ ^git@ ]]; then
    REMOTE_URL="$TARGET"
else
    if [ -n "$TOKEN" ]; then
        REMOTE_URL="https://${TOKEN}@github.com/${TARGET}.git"
    else
        REMOTE_URL="https://github.com/${TARGET}.git"
    fi
fi

echo "[*] Setting remote origin to: $REMOTE_URL (token masked if present)"
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"

echo "[*] Verifying branch..."
git branch -M main

echo "[*] Pushing to GitHub (main branch)..."
git push -u origin main

echo ""
echo "================================================================="
echo "✅ SUCCESS! Repository pushed to: $TARGET"
echo "To view your web app on GitHub Pages, go to Settings -> Pages"
echo "and select 'GitHub Actions' as the deployment source."
echo "================================================================="
