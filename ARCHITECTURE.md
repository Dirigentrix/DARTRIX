# DARTRIX OS v2.0 - Architektura

## Jeden obieg

```
[EVENT] -> [SOIF] -> [KERNEL] -> [ADAPTER] -> [REPLAY]
```

## Komponenty

- **SOIF** - Immutable log, single source of truth. Każde zdarzenie jest zapisywane i nigdy nie jest modyfikowane.
- **KERNEL** - Deterministyczny scheduler stanów. Jedyny kernel w systemie.
- **ADAPTER** - Wymienne adaptery: Allegro, LLM, VSM, File.
- **REPLAY** - Odtwarzanie stanu dla debug/audytu na podstawie logu SOIF.

---

Daniel Adrian Ratajczyk / Dirigentrix
