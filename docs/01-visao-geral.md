# Visão geral

## O problema

A farmácia de um hospital precisa decidir **quanto comprar de cada medicamento**. Comprar pouco
causa falta (paciente sem remédio); comprar muito causa perda por vencimento e capital parado.
Hoje a decisão costuma ser feita olhando a média de consumo recente, o que não acompanha
sazonalidade (gripe no inverno, dengue no verão), feriados e mudanças de tendência.

## A solução: PharmaPredict

Sistema web de gestão de estoque da farmácia hospitalar com **previsão de demanda por
aprendizado de máquina**:

- **Previsão de consumo** dos próximos 7 dias para cada medicamento (LightGBM).
- **Alertas** de risco de falta e de lotes perto do vencimento.
- **Controle de estoque** por lote (FEFO: primeiro que vence, primeiro que sai).
- **Leitor de código de barras** pela câmera para localizar ou cadastrar produtos.
- **Dashboard** com indicadores e tela **Modelo** com a avaliação do modelo.

## Telas

| Tela | Rota | O que mostra |
|---|---|---|
| Login | `/login` | Autenticação (JWT) |
| Dashboard | `/` | KPIs, risco de falta, vencimentos, tendência de consumo |
| Produtos | `/products` | Catálogo, cadastro, edição, detalhes |
| Ler código | `/products/scan` | Leitura por câmera ou digitação |
| Estoque | `/inventory` | Lotes por validade (FEFO), linha do tempo, exportação |
| Previsões | `/predictions` | Previsão dos próximos 7 dias por produto |
| Modelo | `/model` | Acurácia, real × previsto, erro por categoria, variáveis mais importantes |
| Alertas | `/alerts` | Alertas e regras |
| Relatórios | `/reports` | Planilhas CSV (estoque, risco de falta, vencimentos, previsões, alertas) |
| Usuários | `/users` | Gestão de usuários (somente admin) |
| Configurações | `/settings` | Perfil, troca de senha, dados do modelo |

## Dados

O projeto usa uma **base fictícia** que simula um hospital de 350 leitos com 500 medicamentos e o
consumo diário de 01/01/2021 a 29/10/2026. A simulação reproduz padrões reais de farmácia
hospitalar (sazonalidade, surtos, fins de semana, feriados, diferenças entre UTI, PS, enfermaria e
ambulatório). Detalhes em [05-pipeline-ml.md](05-pipeline-ml.md).

## Perfis de acesso

| Perfil | Pode |
|---|---|
| `pharmacist` | Consultar, registrar consumo e movimentações, reconhecer alertas |
| `manager` | Tudo do farmacêutico + criar/editar produtos e lotes |
| `admin` | Tudo + excluir produtos e gerenciar usuários |
