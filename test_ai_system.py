"""
Script de teste rápido para o sistema de mensagens com IA
"""

import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from ai_messages import AIMessageGenerator
from message_bubble import MessageBubbleManager


def test_complete_system():
    """Teste completo: geração + visualização"""
    print("=" * 60)
    print("TESTE COMPLETO DO SISTEMA DE MENSAGENS COM IA")
    print("=" * 60)

    # Initialize Qt application
    app = QApplication(sys.argv)

    # Initialize components
    print("\n1. Inicializando gerador de mensagens...")
    generator = AIMessageGenerator()

    print("\n2. Inicializando gerenciador de balões...")
    bubble_manager = MessageBubbleManager()

    print("\n" + "=" * 60)
    print(f"Ollama disponível: {'✅ SIM' if generator.ollama_available else '❌ NÃO (usando fallback)'}")
    print("=" * 60)

    # Test scenarios
    scenarios = [
        {
            "name": "🌅 Início do dia",
            "ml": 200,
            "goal": 2500,
            "minutes": 10
        },
        {
            "name": "📊 Progresso médio",
            "ml": 1200,
            "goal": 2500,
            "minutes": 30
        },
        {
            "name": "🎯 Quase lá!",
            "ml": 2200,
            "goal": 2500,
            "minutes": 15
        },
        {
            "name": "🏆 Meta batida!",
            "ml": 2600,
            "goal": 2500,
            "minutes": 5
        },
        {
            "name": "⚠️ Esqueceu de beber",
            "ml": 800,
            "goal": 2500,
            "minutes": 70
        }
    ]

    scenario_index = [0]

    def show_next_scenario():
        if scenario_index[0] < len(scenarios):
            scenario = scenarios[scenario_index[0]]

            print(f"\n{'=' * 60}")
            print(f"Cenário {scenario_index[0] + 1}/{len(scenarios)}: {scenario['name']}")
            print(f"Status: {scenario['ml']}ml / {scenario['goal']}ml")
            print(f"Última vez: há {scenario['minutes']} minutos")
            print("-" * 60)

            # Generate message
            message = generator.generate_message(
                scenario['ml'],
                scenario['goal'],
                scenario['minutes']
            )

            print(f"💬 Mensagem: \"{message}\"")
            print("-" * 60)

            # Show bubble
            bubble_manager.show_message(message, duration_ms=5000)

            scenario_index[0] += 1

            # Schedule next scenario
            if scenario_index[0] < len(scenarios):
                QTimer.singleShot(6000, show_next_scenario)
            else:
                print("\n" + "=" * 60)
                print("✅ TESTE CONCLUÍDO!")
                print("=" * 60)
                print("\nDicas:")
                print("- Clique no balão para fechá-lo manualmente")
                print("- Para usar IA, instale Ollama: https://ollama.com")
                print("- Execute: ollama pull llama3.2:1b")
                print("- Edite personalities/default.txt para mudar o tom")
                print("\nFechando em 5 segundos...")
                QTimer.singleShot(5000, app.quit)

    # Start test
    print("\nIniciando teste em 2 segundos...")
    print("(Clique nos balões para fechá-los manualmente)")
    QTimer.singleShot(2000, show_next_scenario)

    sys.exit(app.exec_())


if __name__ == "__main__":
    test_complete_system()
