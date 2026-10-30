# Leitor de código de barras


- Campo `barcode` opcional e único na tabela `products`.
- Migração Alembic `003_product_barcode.py`.
- Endpoint autenticado `GET /api/v1/products/by-barcode/{barcode}`.
- Botão **Ler código** na página original de produtos.
- Página `/products/scan`, com câmera (biblioteca `@zxing/browser`, funciona em qualquer navegador moderno) e opção de digitar o código manualmente.
- Cadastro do produto usando o endpoint já existente.
- Ajuste no login para enviar `username` e `password` como `application/x-www-form-urlencoded`, formato esperado pelo FastAPI `OAuth2PasswordRequestForm`.

## Como executar no Windows

1. Abra o Docker Desktop.
2. No terminal do VS Code, na pasta principal do projeto, execute:

   ```powershell
   docker compose up -d
   ```

3. Em outro terminal, execute o backend conforme o README principal. Se o backend já estiver no ar, pare-o antes de iniciar outra instância.
4. Em outro terminal:

   ```powershell
   cd frontend
   npm.cmd install
   npm.cmd run dev
   ```

5. Acesse `http://localhost:3000`, entre na conta e abra **Produtos → Ler código**. A rota direta é `http://localhost:3000/products/scan`.

## Banco de dados existente

Antes de usar o leitor em uma base já criada, aplique a migração a partir da pasta `backend`:

```powershell
uv run alembic upgrade head
```

Se o backend estiver em um container, execute o comando dentro do ambiente do backend que tem o `uv` e a configuração de banco do projeto. Não use `full_reset.py` apenas para adicionar o leitor, pois um reset pode apagar dados.

## Notas

- A câmera precisa de permissão do navegador. `localhost` é considerado contexto seguro pelos navegadores modernos.
- A leitura pela câmera usa a biblioteca `@zxing/browser` (UPC-A, EAN-13, EAN-8 e Code 128). Se a câmera não abrir, use a entrada manual.
- O código de barras normalmente identifica a embalagem, mas não fornece sozinho o nome, princípio ativo ou validade. Para isso é necessário consultar uma base de dados confiável ou preencher os campos no cadastro.
- O endpoint de consulta requer login. O cadastro também respeita as permissões já definidas pela API.
