#!/bin/bash

# Documentation Size Monitor
# Replicates the GitHub Actions workflow functionality locally
# Analyzes documentation size and checks against configured thresholds

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Thresholds (same as in workflow)
MAX_TOTAL_SIZE_KB=150
MAX_FILE_SIZE_KB=20
MAX_FILES=15

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "📚 Documentation Size Monitor"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create reports directory
mkdir -p .docs-reports

# Count markdown files (excluding archive)
FILE_COUNT=$(find docs -name "*.md" -not -path "docs/archive/*" 2>/dev/null | wc -l)

# Calculate total size in KB (excluding archive)
TOTAL_SIZE=$(find docs -name "*.md" -not -path "docs/archive/*" 2>/dev/null -exec cat {} \; | wc -c)
TOTAL_SIZE_KB=$((TOTAL_SIZE / 1024))

# Estimate token count (rough: 1 token per 4 bytes)
ESTIMATED_TOKENS=$((TOTAL_SIZE / 4))

# Calculate average file size
if [ $FILE_COUNT -gt 0 ]; then
  AVG_SIZE=$((TOTAL_SIZE / FILE_COUNT))
  AVG_SIZE_KB=$((AVG_SIZE / 1024))
else
  AVG_SIZE_KB=0
fi

# Get largest files
LARGEST_FILES=$(find docs -name "*.md" -not -path "docs/archive/*" 2>/dev/null -exec wc -c {} \; | sort -rn | head -5 | awk '{printf "%s (%d KB)\n", $2, int($1/1024)}')

# Print summary
echo "📊 Documentation Statistics:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  Total Files:        ${BLUE}%d${NC}\n" "$FILE_COUNT"
printf "  Total Size:         ${BLUE}%d KB${NC}\n" "$TOTAL_SIZE_KB"
printf "  Estimated Tokens:   ${BLUE}~%d${NC}\n" "$ESTIMATED_TOKENS"
printf "  Average File Size:  ${BLUE}%d KB${NC}\n" "$AVG_SIZE_KB"
echo ""

echo "📈 Largest Files:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$LARGEST_FILES"
echo ""

# Check thresholds
ALERTS=""
HAS_ALERTS=false

if [ $TOTAL_SIZE_KB -gt $MAX_TOTAL_SIZE_KB ]; then
  ALERTS="${ALERTS}⚠️  Total documentation size (${TOTAL_SIZE_KB} KB) exceeds threshold (${MAX_TOTAL_SIZE_KB} KB)\n"
  HAS_ALERTS=true
fi

if [ $FILE_COUNT -gt $MAX_FILES ]; then
  ALERTS="${ALERTS}⚠️  Number of documentation files (${FILE_COUNT}) exceeds threshold (${MAX_FILES})\n"
  HAS_ALERTS=true
fi

# Check for oversized individual files
OVERSIZED=$(find docs -name "*.md" -not -path "docs/archive/*" 2>/dev/null -size +${MAX_FILE_SIZE_KB}k -exec basename {} \;)
if [ -n "$OVERSIZED" ]; then
  ALERTS="${ALERTS}⚠️  Files exceeding ${MAX_FILE_SIZE_KB} KB:\n$(echo "$OVERSIZED" | sed 's/^/     - /')\n"
  HAS_ALERTS=true
fi

# Print status and alerts
echo "📋 Threshold Limits:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  Max Total Size:     ${BLUE}%d KB${NC}\n" "$MAX_TOTAL_SIZE_KB"
printf "  Max File Size:      ${BLUE}%d KB${NC}\n" "$MAX_FILE_SIZE_KB"
printf "  Max File Count:     ${BLUE}%d${NC}\n" "$MAX_FILES"
echo ""

if [ "$HAS_ALERTS" = true ]; then
  printf "${RED}❌ Status: THRESHOLDS EXCEEDED${NC}\n"
  echo ""
  echo "⚠️  Alerts:"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo -e "$ALERTS"
  echo ""
else
  printf "${GREEN}✅ Status: Within acceptable limits${NC}\n"
  echo ""
fi

# Generate report
python3 ".scripts/generate-docs-size-report.py" \
  --file-count "$FILE_COUNT" \
  --total-size-kb "$TOTAL_SIZE_KB" \
  --estimated-tokens "$ESTIMATED_TOKENS" \
  --avg-size-kb "$AVG_SIZE_KB" \
  --largest-files "$LARGEST_FILES" \
  --has-alerts "$HAS_ALERTS" \
  --alerts "$ALERTS"

echo "📁 Reports saved to: .docs-reports/"
echo "   • docs-size-report.md (human-readable)"
echo ""

# Exit with 0 even if alerts (we don't fail the build, just report)
exit 0
