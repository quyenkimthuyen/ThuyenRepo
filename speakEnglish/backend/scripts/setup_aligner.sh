#!/usr/bin/env bash
# Setup script for Gentle or MFA aligners (optional).
# Run manually — do NOT auto-install in CI.

set -euo pipefail

METHOD="${1:-gentle}"

echo "=== PronounceLab Aligner Setup: $METHOD ==="

if [ "$METHOD" = "gentle" ]; then
    echo ""
    echo "Gentle setup (recommended fallback):"
    echo "  1. Install Docker: https://docs.docker.com/get-docker/"
    echo "  2. Run Gentle:"
    echo "     docker run -d --name gentle -p 8765:8765 lowerquality/gentle"
    echo "  3. Set environment:"
    echo "     export ALIGNMENT_METHOD=gentle"
    echo "     export GENTLE_URL=http://localhost:8765"
    echo ""
    echo "Or build from source: https://github.com/lowerquality/gentle"

elif [ "$METHOD" = "mfa" ]; then
    echo ""
    echo "Montreal Forced Aligner setup:"
    echo "  1. Install conda/miniconda"
    echo "  2. Create environment:"
    echo "     conda create -n mfa -c conda-forge montreal-forced-aligner"
    echo "  3. Download models:"
    echo "     mfa model download acoustic english_us_arpa"
    echo "     mfa model download dictionary english_us_arpa"
    echo "  4. Set environment:"
    echo "     export ALIGNMENT_METHOD=mfa"
    echo ""
    echo "Docs: https://montreal-forced-aligner.readthedocs.io/"

else
    echo "Usage: ./setup_aligner.sh [gentle|mfa]"
    echo "Default (no aligner): ALIGNMENT_METHOD=fallback — works out of the box."
fi

echo ""
echo "=== Current default: fallback (proportional alignment) ==="
echo "Backend works without Gentle/MFA for demo purposes."
