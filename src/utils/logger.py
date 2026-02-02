# src/utils/logger.py
# ⚠️ TEACHER'S TEMPLATE - DO NOT MODIFY CORE LOGIC

import json
import os
import uuid
from datetime import datetime
from enum import Enum

# Chemin du fichier de logs
LOG_FILE = os.path.join("logs", "experiment_data.json")

class ActionType(str, Enum):
    """
    Énumération des types d'actions possibles pour standardiser l'analyse.
    """
    ANALYSIS = "CODE_ANALYSIS"  # Audit, lecture, recherche de bugs
    GENERATION = "CODE_GEN"     # Création de nouveau code/tests/docs
    DEBUG = "DEBUG"             # Analyse d'erreurs d'exécution
    FIX = "FIX"                 # Application de correctifs

def log_experiment(agent_name: str, model_used: str, action: ActionType, details: dict, status: str):
    """
    Enregistre une interaction d'agent pour l'analyse scientifique.

    Args:
        agent_name (str): Nom de l'agent (ex: "Auditor", "Fixer").
        model_used (str): Modèle LLM utilisé (ex: "gemini-1.5-flash").
        action (ActionType): Le type d'action effectué (utiliser l'Enum ActionType).
        details (dict): Dictionnaire contenant les détails. DOIT contenir 'input_prompt' et 'output_response'.
        status (str): "SUCCESS" ou "FAILURE".

    Raises:
        ValueError: Si les champs obligatoires sont manquants dans 'details' ou si l'action est invalide.
    """
    
    # --- 1. VALIDATION DU TYPE D'ACTION ---
    # Permet d'accepter soit l'objet Enum, soit la chaîne de caractères correspondante
    valid_actions = [a.value for a in ActionType]
    if isinstance(action, ActionType):
        action_str = action.value
    elif action in valid_actions:
        action_str = action
    else:
        raise ValueError(f"❌ Action invalide : '{action}'. Utilisez la classe ActionType (ex: ActionType.FIX).")

    # --- 2. VALIDATION STRICTE DES DONNÉES (Prompts) ---
    # Pour l'analyse scientifique, nous avons absolument besoin du prompt et de la réponse
    # pour les actions impliquant une interaction majeure avec le code.
    if action_str in [ActionType.ANALYSIS, ActionType.GENERATION, ActionType.DEBUG, ActionType.FIX]:
        required_keys = ["input_prompt", "output_response"]
        missing_keys = [key for key in required_keys if key not in details]
        
        if missing_keys:
            raise ValueError(
                f"❌ Erreur de Logging (Agent: {agent_name}) : "
                f"Les champs {missing_keys} sont manquants dans le dictionnaire 'details'. "
                f"Ils sont OBLIGATOIRES pour valider le TP."
            )

    # --- 3. PRÉPARATION DE L'ENTRÉE ---
    # Création du dossier logs s'il n'existe pas
    os.makedirs("logs", exist_ok=True)
    
    entry = {
        "id": str(uuid.uuid4()),  # ID unique pour éviter les doublons lors de la fusion des données
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "model": model_used,
        "action": action_str,
        "details": details,
        "status": status
    }

    # --- 4. LECTURE & ÉCRITURE ROBUSTE ---
    data = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content: # Vérifie que le fichier n'est pas juste vide
                    data = json.loads(content)
        except json.JSONDecodeError:
            # Si le fichier est corrompu, on repart à zéro (ou on pourrait sauvegarder un backup)
            print(f"⚠️ Attention : Le fichier de logs {LOG_FILE} était corrompu. Une nouvelle liste a été créée.")
            data = []

    data.append(entry)
    
    # Écriture
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ============================================
# HELPER FUNCTIONS (Optional - for debugging)
# ============================================

def get_experiment_logs() -> list:
    """
    Retrieve all experiment logs
    Useful for debugging and validation
    """
    if not os.path.exists(LOG_FILE):
        return []
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def validate_logs() -> tuple[bool, list[str]]:
    """
    Validate that all logs have required fields
    Returns: (is_valid, list_of_errors)
    """
    logs = get_experiment_logs()
    errors = []
    
    for i, log in enumerate(logs):
        # Check mandatory fields
        if "input_prompt" not in log.get("details", {}):
            errors.append(f"Log #{i} (id: {log.get('id', 'unknown')}): Missing 'input_prompt'")
        
        if "output_response" not in log.get("details", {}):
            errors.append(f"Log #{i} (id: {log.get('id', 'unknown')}): Missing 'output_response'")
        
        if "action" not in log:
            errors.append(f"Log #{i} (id: {log.get('id', 'unknown')}): Missing 'action'")
        
        # Validate action type
        valid_actions = [a.value for a in ActionType]
        if log.get("action") not in valid_actions:
            errors.append(f"Log #{i}: Invalid action '{log.get('action')}'. Must be one of {valid_actions}")
    
    return len(errors) == 0, errors


def clear_logs() -> None:
    """
    Clear all logs (use for testing)
    """
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    print("🗑️ Logs cleared")


# Example usage
if __name__ == "__main__":
    # Clear old logs
    clear_logs()
    
    # Example: Correct usage
    print("\n✅ Example 1: Correct logging")
    log_experiment(
        agent_name="Auditor_Agent",
        model_used="gemini-2.5-flash",
        action=ActionType.ANALYSIS,
        details={
            "file_analyzed": "messy_code.py",
            "input_prompt": "You're a Python expert. Analyze this code...",
            "output_response": "I detected a missing docstring...",
            "issues_found": 3
        },
        status="SUCCESS"
    )
    
    # Example: Using DEBUG action
    print("\n✅ Example 2: DEBUG action")
    log_experiment(
        agent_name="Debugger_Agent",
        model_used="gpt-4",
        action=ActionType.DEBUG,
        details={
            "input_prompt": "Debug this error: NameError...",
            "output_response": "The variable 'x' is undefined...",
            "error_type": "NameError"
        },
        status="SUCCESS"
    )
    
    # Example: Missing required field (will raise error)
    print("\n❌ Example 3: Missing input_prompt (should fail)")
    try:
        log_experiment(
            agent_name="Bad_Agent",
            model_used="gpt-4",
            action=ActionType.FIX,
            details={
                # "input_prompt": "MISSING!",  # This will cause error
                "output_response": "Fixed code..."
            },
            status="SUCCESS"
        )
    except ValueError as e:
        print(f"   Expected error: {e}")
    
    # Validate logs
    print("\n" + "="*60)
    print("🔍 VALIDATING LOGS")
    print("="*60)
    is_valid, errors = validate_logs()
    
    if is_valid:
        print("✅ All logs are valid!")
    else:
        print("❌ Validation errors found:")
        for error in errors:
            print(f"  - {error}")
    
    # Display logs
    print("\n" + "="*60)
    print("📝 CURRENT LOGS")
    print("="*60)
    logs = get_experiment_logs()
    print(json.dumps(logs, indent=2, ensure_ascii=False))