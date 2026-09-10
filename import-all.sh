#!/usr/bin/env bash
# ==============================================================================
# TechQueue Interview Coach — Import Script
# Imports all tools, flows, knowledge bases, and agents into watsonx Orchestrate.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "======================================================"
echo " TechQueue Interview Coach — Importing to watsonx Orchestrate"
echo "======================================================"

# ------------------------------------------------------------------------------
# 1. Import Knowledge Base
# ------------------------------------------------------------------------------
echo ""
echo "[1/4] Importing Knowledge Base ..."
orchestrate knowledge-bases import -f "${SCRIPT_DIR}/knowledge_base/interview_knowledge_base.yaml"
echo "  ✓ interview_knowledge_base imported"

# ------------------------------------------------------------------------------
# 2. Import Python Tools
# ------------------------------------------------------------------------------
echo ""
echo "[2/4] Importing Python Tools ..."

for tool_file in profile_tools.py evaluation_tools.py; do
  orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/${tool_file}"
  echo "  ✓ ${tool_file} imported"
done

# ------------------------------------------------------------------------------
# 3. Import Flow Tool
# ------------------------------------------------------------------------------
echo ""
echo "[3/4] Importing Flow Tool ..."

orchestrate tools import -k flow -f "${SCRIPT_DIR}/tools/interview_prep_flow.py"
echo "  ✓ interview_prep_flow.py imported"

# ------------------------------------------------------------------------------
# 4. Import Agent
# ------------------------------------------------------------------------------
echo ""
echo "[4/4] Importing Agent ..."
orchestrate agents import -f "${SCRIPT_DIR}/agents/techqueue_interview_coach.yaml"
echo "  ✓ techqueue_interview_coach agent imported"

# ------------------------------------------------------------------------------
# Done
# ------------------------------------------------------------------------------
echo ""
echo "======================================================"
echo " Import complete! Start chatting with TechQueue:"
echo "   orchestrate chat start"
echo "   → Select: techqueue_interview_coach"
echo "======================================================"
