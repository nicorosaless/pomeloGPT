Perfecto. Aquí tienes el **README.md completo**, listo para usar. Está pensado como si fuera la documentación pública de PomeloGPT. Es profesional, claro, y refleja exactamente la arquitectura que definiste.

---

# **PomeloGPT**

Asistente local privado basado en modelos de Ollama, con RAG optimizado para modelos pequeños y una interfaz minimalista de escritorio construida con Electron.

## **Descripción**

PomeloGPT es una aplicación de escritorio para macOS que permite ejecutar modelos LLM locales mediante **Ollama**, con un sistema RAG altamente optimizado para modelos pequeños como **Gemma3 4B** y otros que el usuario tenga instalados.

La app funciona completamente **offline**, sin telemetría, ni envío de datos. Todos los documentos, índices, modelos y conversaciones permanecen en tu máquina.

Diseño minimalista. Sin distracciones. Todo rápido.

---

# **Características principales**

### **1. Chat local con modelos Ollama**

* Funciona con cualquier modelo instalado en Ollama.
* Selector de modelos integrado.
* Configuración rápida (temperatura, top_p, max_tokens, etc.).
* Streaming de tokens fluido.

### **2. RAG optimizado para modelos pequeños**

Diseñado para sacar el máximo rendimiento a modelos de 4–7B:

* Hybrid retrieval: BM25 + vector search.
* Embeddings locales con modelos ligeros.
* Reranker mínimo para precisión en modelos pequeños.
* Chunking dinámico y eficiente.
* Pipeline afinado para latencia baja y calidad alta.
* OCR integrado para PDFs mediante un modelo tipo DeepSeek OCR.

### **3. Websearch opcional**

* Botón tipo “globo terráqueo” para activar/desactivar websearch por mensaje.
* API configurable (Tavily, Brave o SerpAPI).
* Resultados procesados y resumidos antes de pasarse al LLM.

### **4. Knowledge Base Manager**

* Subida de documentos (PDF, TXT, Markdown).
* OCR automático para PDFs escaneados.
* Lista de documentos indexados.
* Reindexación, borrado y limpieza sencilla.
* Visualización básica de chunks y metadatos.

### **5. Ollama Manager**

* Lista de modelos instalados en Ollama.
* Botones para instalar, eliminar y actualizar modelos.
* Selección rápida de modelo por defecto.
* Información de tamaño, quantización y parámetros.

### **6. Privacidad absoluta**

* Todo se ejecuta localmente.
* No se envía nada a servidores externos.
* No hay telemetría, tracking, ni analítica.
* Los índices se guardan en disco local; almacenamiento cifrado opcional.

### **7. Multiplataforma (roadmap)**

* **macOS** soportado desde el primer día.
* Windows y Linux previstos (la arquitectura ya está preparada).

---

# **Arquitectura técnica**

## **Visión general**

```
Electron (UI minimalista)
        ↓
React + Vite frontend
        ↓
FastAPI backend embebido (Python)
        ↓
Ollama (modelos locales)
        ↓
RAG System (embeddings + vector DB + reranker + OCR)
```

---

# **Componentes**

## **Frontend (Electron + React)**

* Chat UI con streaming.
* Editor minimalista.
* Selector de modelo y configuración.
* Panel de documentos.
* Ollama Manager.
* Toggle de Websearch.
* Barra lateral para modos: Chat / RAG / Modelos / Documentos.

## **Backend (FastAPI embebido en Electron)**

Responsable de:

* Llamadas a Ollama (stream).
* Ingestión de documentos.
* OCR para PDFs.
* Embeddings.
* Vectorstore (Chroma o LanceDB).
* Recuperación híbrida.
* Reranking.
* Construcción de prompts.
* Websearch (si está activado).
* Gestión de modelos Ollama.

---

# **RAG Pipeline**

1. **Ingesta**

   * OCR si es PDF escaneado.
   * Limpieza, normalización y segmentación en chunks de 400–800 tokens.
   * Overlap: 80–120 tokens.

2. **Embeddings locales**

   * Modelo ligero tipo `nomic-embed-text`.
   * Normalización L2.

3. **Vectorstore**

   * Chroma local por defecto.
   * Indexación incremental.

4. **Hybrid search**

   * BM25 lexical filter para eliminar ruido.
   * Vector search en top-k filtrado.

5. **Reranker**

   * Modelo pequeño CPU-friendly.
   * Selección final de 5–8 chunks.

6. **Prompt final**

   * Plantillas optimizadas para modelos pequeños.
   * Minimización del contexto para reducir ruido.
   * Instrucciones de precisión y citas.

7. **Generación**

   * Streaming desde Ollama.
   * Postprocesado mínimo.

---

# **Instalación**

1. Instalar **Ollama** manualmente o desde la app:

```
https://ollama.com/download
```

2. En la app:

```
Settings → Ollama Manager → Install model
```

Ejemplo:

```
Gemma3 4B (Q4_K_M)
```

3. Abrir PomeloGPT.
   Listo.

---

# **Comandos disponibles (CLI opcional)**

```
pomelogpt ingest <file>
pomelogpt index rebuild
pomelogpt models list
pomelogpt models pull gemma3:4b
```

*(Feature opcional para desarrolladores.)*

---

# **Estructura del proyecto**

```
pomelogpt/
├─ apps/
│  ├─ electron-shell/
│  └─ web-ui/
├─ backend/
│  ├─ api/
│  ├─ rag/
│  ├─ embeddings/
│  ├─ vectorstore/
│  └─ ocr/
├─ scripts/
├─ infra/
└─ README.md
```

---

# **Modo privado**

* Sin telemetría.
* Sin red salvo que actives Websearch.
* Todo local.

---

# **Roadmap**

### **v1.0**

* RAG completo.
* Chat + streaming.
* Selector de modelos.
* OCR.
* Websearch opcional.
* Index manager.

### **v1.1**

* Empaquetado para Windows.
* Config avanzada de RAG.
* Export/import de bases de conocimiento.

### **v2.0**

* Modo “server local” para conectar desde móvil.
* Plugins locales.
* Multi-usuario local (opcional).

---

# **Licencia**

Por definir.

---

# **Estado actual**

### **Implementado**
*   **Backend**: FastAPI server running locally.
*   **Ollama Manager**:
    *   List installed models.
    *   Install new models with progress tracking.
    *   Delete models.
    *   **Enhanced UI**: Performance badges (Velocity/Quality) based on M1 Pro benchmarks.
    *   **Visual Configuration**: Quantization selection with detailed descriptions.
*   **Frontend**: React + Vite + Electron setup.

### **En progreso**
*   **Chat Interface**:
    *   Integration with Ollama for inference.
    *   Model selector in input bar.
    *   Web search toggle in input bar.
    *   Collapsible Knowledge Base panel.

### **Pendiente**
*   RAG Pipeline implementation.
*   Web search integration.
*   Document ingestion and OCR.