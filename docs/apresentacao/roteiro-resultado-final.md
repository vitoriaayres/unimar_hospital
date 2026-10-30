# Roteiro: apresentação do resultado final

Foco: **o sistema funcionando e o resultado do modelo**. Sugestão para ~15 minutos, com o sistema
rodando ao vivo (ver "Antes de começar" no [roteiro de código](roteiro-codigo-e-documentacao.md)).

## 1. O problema (1 min)

Falta de medicamento × perda por vencimento. Hoje a compra é guiada pela média de consumo recente.

## 2. Demo do sistema (6 min)

Login `admin@hospital.gov.br` / `admin123`, depois:

1. **Dashboard:** indicadores, produtos com risco de falta, vencimentos próximos.
2. **Produtos → Ler código:** apontar a câmera para uma caixa de remédio (ou digitar o código).
3. **Estoque:** lotes por validade (FEFO).
4. **Previsões:** escolher um produto e mostrar a previsão dos próximos dias.
5. **Alertas:** reconhecer um alerta.

## 3. Resultado do modelo (5 min)

Abrir a tela **Modelo** (`/model`). Os mesmos gráficos estão em `docs/imagens/` para os slides.

| Gráfico | Mensagem |
|---|---|
| Cards do topo | "O modelo erra X%; o método atual erra Y%; redução de Z pontos." |
| Real × previsto | As linhas do modelo e do consumo real andam juntas, inclusive nos picos sazonais. |
| Erro por categoria | O modelo ganha do método atual em todas as categorias. |
| Variáveis mais importantes | O modelo aprendeu o que faz sentido: consumo recente, médias e sazonalidade. |

Os números atualizados estão em [05-pipeline-ml.md → Resultados](../05-pipeline-ml.md#resultados).

## 4. Fechamento (2 min)

- **Entregue:** gestão de estoque, alertas, leitor de código de barras, previsão com ML.
- **Próximos passos:** usar o histórico real do hospital, agendar o pipeline diariamente, sugestão
  automática de pedido de compra.

## Plano B (se algo falhar ao vivo)

- Sem câmera: digitar o código de barras na mesma tela.
- Sem sistema: usar as imagens de `docs/imagens/` e prints das telas.
