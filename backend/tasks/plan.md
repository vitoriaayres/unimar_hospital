# Plano: Melhoria do Gerador de Dados Sinteticos e Treinamento ML

## Problemas Identificados
1. Distribuicao uniforme artificial entre departamentos
2. Falta de distribuicao de Pareto (20% dos produtos = 80% do consumo)
3. Sazonalidade fraca
4. Sem outliers/eventos especiais
5. Movimentacoes sinteticas (todas em 1 dia)
6. Proporcao de prescricao identica em todos os departamentos

## Fase 1: Melhorias no Gerador Sintetico
- Tarefa 1: Distribuicao de Pareto para demanda
- Tarefa 2: Sazonalidade realista por classe ATC
- Tarefa 3: Outliers e eventos especiais
- Tarefa 4: Distribuicao por departamento mais realista

## Fase 2: Pipeline ML
- Tarefa 5: Re-gerar dados sinteticos melhorados
- Tarefa 6: Re-treinar modelo e avaliar metricas
- Tarefa 7: Ajustar features se necessario

## Fase 3: Integracao TUI
- Tarefa 8: Integrar previsoes na interface TUI
- Tarefa 9: Testar fluxo completo
