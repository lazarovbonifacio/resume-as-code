# Currículos Modulares (Modelo Harvard)

Repositório organizado no formato de **blocos de montar** a partir de um único arquivo central ([`master.md`](master.md)).

## Estrutura & Regras

- [`master-template.md`](master-template.md) — Esqueleto documentado com as regras do repositório.
- [`master.md`](master.md) — Fonte única da verdade (PT_BR e EN_US) com blocos identificados por `[id]` e `tags`.
- [`build.py`](build.py) — Gerador de currículos (`.md` + `.pdf` no padrão Harvard OCS) com validação de **máximo de 2 páginas** (`MAX_PAGES = 2`) e checagem da fórmula dos bullets:
  - **`**[Verbo de Ação]** + [Resultado] + **[Métrica OU Conquista/Promoção/Reconhecimento]** + **[Ferramentas]**`**
- `dist/` — Currículos gerados prontos para envio (`.md` e `.pdf`).
- `archive/` — Versões antigas preservadas.

## Uso Rápido

```bash
# Validar fórmula dos bullets, seção Career Break e limite de 2 páginas
./build.py --check

# Gerar todos os 12 currículos padrão (6 cargos x 2 idiomas) em dist/
./build.py --all

# Gerar para um cargo e idioma específicos
# Cargos: sre, platform, devops, devsecops, cloud, infra
# Idiomas: pt_br, en_us
./build.py --role sre --lang pt_br

# Personalizar para uma vaga/empresa (incluindo ou ocultando blocos, ex.: Career Break)
./build.py --role platform --lang en_us \
  --company "Stripe" \
  --title "Senior Platform Infrastructure Engineer" \
  --blocks proj-asus \
  --exclude cb-cloud-transition,bd-infra

# Listar todos os blocos disponíveis no master.md
./build.py --list
```
