#!/bin/bash

SKILLS=(
    "vercel-labs/skills@find-skills"
    "nextlevelbuilder/ui-ux-pro-max-skill@ui-ux-pro-max"
    "vercel-labs/agent-skills@vercel-react-best-practices"
    "vercel/turborepo@turborepo"
    "mattpocock/skills@grill-me"
    "umputun/revdiff@revdiff"
    "anthropics/skills@webapp-testing"
    "obra/superpowers@test-driven-development"
    "wondelai/skills@domain-driven-design"
)

for skill in "${SKILLS[@]}"; do
    npx skills add $skill -g
done
