# Velabody · edición de reels

Reels verticales para la marca **Velabody** (1080x1920, Premiere Pro). Este repositorio tiene **la wiki del proyecto, las herramientas y el guion y el plan de cada video**. El material pesado (videos, música, el `.prproj` y los exportados) **no está acá**: se comparte por Drive.

## Qué hay

| Carpeta | Qué es |
|---|---|
| `_WIKI/` | **La wiki**: estilo, reglas de la clienta, flujo de trabajo, ejemplos y recursos. Se abre con Obsidian. Empezar por `00_INICIO.md`. |
| `CLAUDE.md` | Instrucciones para Claude Code: lee la wiki antes de editar. |
| `_HERRAMIENTAS/` | Scripts (transcripción, armado y brief) y el panel *VELABODY Builder* de Premiere. |
| `Video N — …/` | Solo `guion.md` y `_EDICION/plan*.json` de cada video. |

## Abrir la wiki en Obsidian

1. Clonar el repo (*GitHub Desktop › Clone*, o `git clone <url>`).
2. En Obsidian, ir a *Manage vaults › Open folder as vault* y elegir la carpeta **`_WIKI`** de este repo.
3. Es una bóveda separada: no se mezcla con otros proyectos de Obsidian.

## Trabajar juntos

- Antes de empezar: **traer los cambios** (*Fetch/Pull* en GitHub Desktop, o `git pull`).
- Después de cambiar algo en la wiki: **subirlo** (*Commit* + *Push*, o `git add -A && git commit -m "…" && git push`).
- Si cambia un criterio que vale para todos los videos, se edita la página que corresponde y se anota en `_WIKI/07_decisiones.md`.

## Rutas

Las herramientas y la wiki asumen que el proyecto está en **`E:\VELABODY`**. Algunos recursos (MOGRT de Mister Horse, el click de títulos) apuntan a rutas de la compu de Juli. Si trabajás en otra ubicación, copiá `_HERRAMIENTAS/config_local.ejemplo.json` como `config_local.json` (no se versiona) y poné ahí tu raíz y tus recursos. Los planes pueden usar `"carpeta"` relativa a esa raíz.
