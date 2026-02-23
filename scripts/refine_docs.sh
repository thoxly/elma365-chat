#!/bin/bash
# Convenience script for docs refinement

cd "$(dirname "$0")/.." || exit 1

case "$1" in
    "all")
        echo "Running complete docs refinement..."
        python pipeline/docs_updater/refine_rules.py --mode all "${@:2}"
        ;;
    "academy")
        echo "Loading academy materials..."
        python pipeline/docs_updater/refine_rules.py --mode academy "${@:2}"
        ;;
    "dictionary")
        echo "Refining dictionary..."
        python pipeline/docs_updater/refine_rules.py --mode dictionary
        ;;
    "architecture")
        echo "Refining architecture rules..."
        python pipeline/docs_updater/refine_rules.py --mode rules --type architecture
        ;;
    "process")
        echo "Refining process rules..."
        python pipeline/docs_updater/refine_rules.py --mode rules --type process
        ;;
    "ui")
        echo "Refining UI rules..."
        python pipeline/docs_updater/refine_rules.py --mode rules --type ui
        ;;
    "validate")
        echo "Validating refined docs..."
        python pipeline/docs_updater/validate_new_rules.py --all
        ;;
    *)
        echo "Usage: $0 {all|academy|dictionary|architecture|process|ui|validate} [options]"
        echo ""
        echo "Commands:"
        echo "  all          - Run complete refinement (academy + dictionary + all rules)"
        echo "  academy      - Load academy materials only"
        echo "  dictionary   - Refine dictionary only"
        echo "  architecture - Refine architecture rules only"
        echo "  process      - Refine process rules only"
        echo "  ui           - Refine UI rules only"
        echo "  validate     - Validate and compare results"
        echo ""
        echo "Options:"
        echo "  --reload     - Force reload academy materials (for 'all' or 'academy')"
        echo ""
        echo "Examples:"
        echo "  $0 all"
        echo "  $0 all --reload"
        echo "  $0 academy --reload"
        echo "  $0 dictionary"
        echo "  $0 validate"
        exit 1
        ;;
esac


