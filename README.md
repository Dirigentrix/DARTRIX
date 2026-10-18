# DARTRIX OS v2.0

> **Deterministyczny Meta-OS dla orkiestracji agentów i procesów biznesowych.**

**Author:** Daniel Adrian Ratajczyk  
**Organization:** Dirigentrix  
**License:** MIT  
**Version:** 2.0-clean (2026-10-18)

---

## Co to jest?

DARTRIX OS to nie framework do agentów. To **system operacyjny** który zarządza agentami, stanem i integracjami w sposób deterministyczny.

Inspiracje: Erlang/Akka (crash-only), Event Sourcing, Viable System Model (Beer), SOIF.

## Architektura

Jeden obieg:

[EVENT] -> [SOIF] -> [KERNEL] -> [ADAPTER] -> [REPLAY]

- **SOIF** - Immutable log, jedyny Source of Truth
- **KERNEL** - Deterministyczny scheduler stanów
- **ADAPTER** - Wymienne adaptery (Allegro, LLM, VSM, File)
- **REPLAY** - Odtwarzanie stanu dla debug/audytu

Pełna spec: zobacz `ARCHITECTURE.md`

## Quick Start

```bash
pip install -r requirements.txt
python start_dartrix.py
python replay.py
python examples/allegro_vsm_demo.py
```

## Struktura v2 (Clean)

```
/README.md, ARCHITECTURE.md, Makefile, requirements.txt, .gitignore
/core/kernel_scheduler.py - JEDYNY kernel
/core/soif_persistence.py - immutable log
/core/trix_router.py
/adapters/
/examples/allegro_vsm_demo.py - główny dowód
/legacy/ - stare wersje
```

## Autor

**Daniel Adrian Ratajczyk** - Dirigentrix  
GitHub: @Dirigentrix

---

*Deterministyczny system zarządzania stanem nie może sam być w stanie superpozycji.*
