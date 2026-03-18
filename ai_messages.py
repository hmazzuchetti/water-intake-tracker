"""
AI Message Generator using Ollama
Generates random contextual messages about hydration
"""

import random
import os
import json
from datetime import datetime


class AIMessageGenerator:
    """Generates messages using Ollama or fallback to pre-written messages"""

    def __init__(self, personality_file: str = "personalities/default.txt"):
        self.personality_file = personality_file
        self.ollama_available = False
        self.ollama = None

        # Get model from config
        from config import CONFIG
        self.ollama_model = CONFIG.get("ai_ollama_model", "llama3.2:1b")

        # Try to connect to Ollama on startup
        success, msg = self.try_reconnect()
        print(f"[AI] Startup: {msg}")

        # Load personality/instructions
        self.personality = self._load_personality()

        # Fallback messages (when Ollama not available)
        self.fallback_messages = self._load_fallback_messages()

    def try_reconnect(self) -> tuple:
        """Tenta (re)conectar ao Ollama.
        Returns: (sucesso: bool, mensagem: str)
        """
        try:
            import ollama
            self.ollama = ollama
            print("[AI DEBUG] OK - Biblioteca ollama importada")

            # Test connection
            print("[AI DEBUG] Testando conexão com ollama.list()...")
            models_response = self.ollama.list()

            # Extract model names (handle different response formats)
            model_names = []

            if hasattr(models_response, 'models'):
                for m in models_response.models:
                    if hasattr(m, 'model'):
                        model_names.append(m.model)
                    elif hasattr(m, 'name'):
                        model_names.append(m.name)
            elif isinstance(models_response, dict) and 'models' in models_response:
                for m in models_response['models']:
                    name = m.get('name') or m.get('model') or str(m)
                    model_names.append(name)

            print(f"[AI DEBUG] OK - Conectado! Modelos disponiveis: {model_names}")

            # Check if our model is available
            model_found = self.ollama_model in model_names or any(self.ollama_model in name for name in model_names)
            if model_found:
                print(f"[AI DEBUG] OK - Modelo {self.ollama_model} encontrado")
            else:
                print(f"[AI DEBUG] AVISO - Modelo {self.ollama_model} nao encontrado")
                if model_names:
                    print(f"[AI DEBUG] Vamos tentar usar mesmo assim...")

            self.ollama_available = True
            return True, f"Conectado! Modelo {self.ollama_model} disponível"

        except ImportError as e:
            print(f"[AI DEBUG] ERRO de import: {e}")
            self.ollama_available = False
            return False, "Biblioteca ollama não instalada (pip install ollama)"

        except Exception as e:
            print(f"[AI DEBUG] ERRO ao conectar: {type(e).__name__}: {e}")
            self.ollama_available = False
            return False, "Ollama não está rodando"

    def _load_personality(self) -> str:
        """Load personality/instruction file for the AI"""
        # Ensure personalities directory exists
        os.makedirs("personalities", exist_ok=True)

        # Create default if doesn't exist
        if not os.path.exists(self.personality_file):
            default_personality = """Você é um assistente divertido e sarcástico que ajuda o usuário a se manter hidratado.

ESTILO:
- Use humor sarcástico mas amigável
- Seja breve (máximo 2 frases, prefira 1 frase)
- Varie entre encorajamento, sarcasmo leve, e curiosidades
- Use emojis ocasionalmente (mas não exagere)
- Seja direto e descontraído

CONTEXTO:
Você receberá informações sobre:
- Quanto o usuário já bebeu hoje
- Quanto falta para a meta
- Há quanto tempo não bebe água

EXEMPLOS DE TOM:
- "Vai morrer desidratado em... brincadeira, bebe água aí 💧"
- "Quase lá! Falta só... tudo isso de novo 😅"
- "Parabéns por não virar uma uva passa hoje!"
- "Seus rins agradecem essa hidratação"
- "H2O é a parada mais importante depois do oxigênio, sabia?"

IMPORTANTE:
- NÃO use formatação Markdown
- NÃO use aspas em volta da mensagem
- Retorne APENAS a mensagem, nada mais
- Máximo de 100 caracteres
"""
            with open(self.personality_file, 'w', encoding='utf-8') as f:
                f.write(default_personality)

        # Load personality
        try:
            with open(self.personality_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"[AI] Erro ao carregar personalidade: {e}")
            return "Você é um assistente amigável que ajuda com hidratação."

    def _load_fallback_messages(self) -> dict:
        """Load fallback messages for when Ollama is not available"""
        return {
            "low_progress": [
                "Bora começar o dia hidratado! 💧",
                "Aquela meta não vai se alcançar sozinha...",
                "Seus rins estão mandando um alô 👋",
                "Lembra da última vez que você bebeu água? Nem eu.",
                "Água: melhor que café (quase)",
            ],
            "medium_progress": [
                "Tá indo bem! Mas não para agora 🚀",
                "Metade do caminho, falta só... a outra metade",
                "Continue assim que vira peixe 🐟",
                "Progresso detectado! Parabéns por ter memória",
                "Você está 60% água, vamos pra 70%?",
            ],
            "high_progress": [
                "Quase lá, campeão! 🏆",
                "Seus rins estão fazendo uma festa",
                "Mais um pouquinho e você vira fonte",
                "Impressionante, você realmente bebe água!",
                "Próximo nível: ser patrocinado por marca de água",
            ],
            "goal_reached": [
                "META BATIDA! Você é incrível! 🎉",
                "Parabéns por não virar uma uva passa!",
                "Nível de hidratação: LENDÁRIO",
                "Seus rins mandaram um e-mail de agradecimento",
                "Achievement unlocked: Ser Humano Funcional 🏅",
            ],
            "reminder": [
                "Psiu... já faz um tempo que não bebe água",
                "Tá esperando o quê? Uma notificação? Aqui está ela!",
                "Aquele momento perfeito pra beber água",
                "Oi, sou sua consciência hidratada 👻",
                "Alerta de desidratação iminente!",
            ],
            "random": [
                "Água é vida, literalmente 💦",
                "Dica: água não tem calorias!",
                "Sabia que o cérebro é 75% água?",
                "Beber água > ler notícias tristes",
                "Plot twist: você precisa de água",
                "Água: o combustível premium do corpo",
                "Hidratação: 10/10, recomendo",
            ]
        }

    def generate_message(self, ml_current: int, ml_goal: int, minutes_since_last: int) -> tuple:
        """
        Generate a contextual message based on current status

        Args:
            ml_current: Current water intake in ml
            ml_goal: Daily goal in ml
            minutes_since_last: Minutes since last drink

        Returns:
            Tuple of (message_string, message_type)
            message_type can be: "celebration", "achievement", "reminder", "normal", "funny"
        """
        percentage = (ml_current / ml_goal) * 100 if ml_goal > 0 else 0

        # Determine message type based on context
        message_type = self._determine_message_type(percentage, minutes_since_last)

        if self.ollama_available:
            message = self._generate_with_ollama(ml_current, ml_goal, percentage, minutes_since_last)
        else:
            message = self._generate_fallback(percentage, minutes_since_last)

        return message, message_type

    def _determine_message_type(self, percentage: float, minutes_since_last: int) -> str:
        """Determine the type of message based on context"""
        if percentage >= 100:
            return "celebration"
        elif percentage >= 50 and percentage < 55:  # Just hit 50%
            return "achievement"
        elif percentage >= 75 and percentage < 80:  # Just hit 75%
            return "achievement"
        elif minutes_since_last > 45:
            return "reminder"
        elif percentage > 70:
            return "normal"  # Close to goal, encouraging
        else:
            # Random chance of funny message
            import random
            if random.random() < 0.3:  # 30% chance
                return "funny"
            return "normal"

    def _generate_with_ollama(self, ml_current: int, ml_goal: int, percentage: float, minutes_since_last: int) -> str:
        """Generate message using Ollama"""
        try:
            print(f"[AI] Gerando mensagem com modelo: {self.ollama_model}")

            # Build context prompt
            context = f"""SITUAÇÃO ATUAL:
- Já bebeu: {ml_current}ml
- Meta diária: {ml_goal}ml
- Progresso: {percentage:.0f}%
- Última vez que bebeu: há {minutes_since_last} minutos

Gere UMA mensagem curta e divertida para o usuário baseado na situação acima."""

            prompt = f"{self.personality}\n\n{context}"

            # Call Ollama
            response = self.ollama.generate(
                model=self.ollama_model,
                prompt=prompt,
                options={
                    "temperature": 0.9,  # More creative
                    "num_predict": 150,  # Max tokens (permite mensagens mais longas)
                }
            )

            message = response['response'].strip()

            # Clean up message
            message = message.replace('"', '').replace("'", "")
            if message.startswith('-'):
                message = message[1:].strip()

            # Não limita mais o tamanho - deixa o arquivo de personalidade controlar
            return message

        except Exception as e:
            print(f"[AI] Erro ao gerar mensagem com Ollama: {e}")
            # Fallback to pre-written messages
            return self._generate_fallback(percentage, minutes_since_last)

    def _generate_fallback(self, percentage: float, minutes_since_last: int) -> str:
        """Generate message from pre-written pool"""

        # Choose category based on context
        if percentage >= 100:
            category = "goal_reached"
        elif percentage >= 70:
            category = "high_progress"
        elif percentage >= 40:
            category = "medium_progress"
        elif minutes_since_last > 45:
            category = "reminder"
        elif percentage > 0:
            category = "low_progress"
        else:
            category = "random"

        # Pick random message from category
        messages = self.fallback_messages.get(category, self.fallback_messages["random"])
        return random.choice(messages)

    def reload_personality(self):
        """Reload personality file (useful after editing)"""
        self.personality = self._load_personality()
        print("[AI] Personalidade recarregada")


def test_generator():
    """Test the message generator"""
    print("=" * 50)
    print("AI Message Generator Test")
    print("=" * 50)

    generator = AIMessageGenerator()

    # Test scenarios
    scenarios = [
        (500, 2500, 15, "Início do dia"),
        (1200, 2500, 30, "Progresso médio"),
        (2000, 2500, 20, "Quase lá"),
        (2600, 2500, 10, "Meta batida!"),
        (800, 2500, 60, "Faz tempo que não bebe"),
    ]

    print(f"\nOllama disponível: {generator.ollama_available}")
    print("-" * 50)

    for ml_current, ml_goal, minutes, description in scenarios:
        print(f"\n{description}:")
        print(f"  Status: {ml_current}ml / {ml_goal}ml ({ml_current/ml_goal*100:.0f}%)")
        print(f"  Última vez: há {minutes} min")
        message = generator.generate_message(ml_current, ml_goal, minutes)
        print(f"  💬 \"{message}\"")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    test_generator()
