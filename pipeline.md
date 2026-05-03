# Book2Vision System Pipeline

Here is the full system architecture and data flow pipeline for Book2Vision, visualized as a Mermaid flowchart. 

```mermaid
graph TD
    %% Define Styles
    classDef userAccess fill:#6b4ce6,stroke:#fff,stroke-width:2px,color:#fff,rx:8px
    classDef process fill:#2a2a35,stroke:#4a4a5a,stroke-width:2px,color:#e1e1e6,rx:8px
    classDef ai fill:#00b8d9,stroke:#fff,stroke-width:2px,color:#000,rx:8px
    classDef storage fill:#36b37e,stroke:#fff,stroke-width:2px,color:#000,rx:8px
    classDef frontend fill:#ffab00,stroke:#fff,stroke-width:2px,color:#000,rx:8px

    %% --- Input Phase ---
    User((User)):::userAccess -->|Uploads PDF/EPUB/TXT| UploadAPI["/api/upload"]:::process
    User -->|Selects existing book| LibraryAPI["/api/library/load"]:::process
    
    UploadAPI --> TextExtraction["Text Extraction & Parsing"]:::process
    TextExtraction --> DB[(SQLite / library.db)]:::storage
    LibraryAPI --> DB
    DB --> MainController["Application State / Controller"]:::process

    %% --- Core Semantic Analysis ---
    MainController -->|Trigger Analysis| SemanticAnalysis["Semantic Analysis Engine"]:::ai
    SemanticAnalysis -->|API Call| Gemini["Gemini LLM (Flash/Pro)"]:::ai
    Gemini -.->|Returns JSON Map| SemanticAnalysis
    
    SemanticAnalysis --> ExtractedData{"Extracted Data"}:::storage
    ExtractedData -->|List of Characters| Entities["Entities (Name, Role, Desc)"]
    ExtractedData -->|Key Plot Points| Scenes["Scenes (Setting, Mood, Desc)"]
    ExtractedData -->|Story Overview| Summary["Story Summary"]

    %% --- Visual Generation Pipeline ---
    ExtractedData --> VisualGen["Visual Generation Dispatcher"]:::process
    VisualGen --> CoverGen["1. Cover Generation"]:::ai
    VisualGen --> EntityGen["2. Entity Portrait Generation"]:::ai
    VisualGen --> SceneGen["3. Scene Generation"]:::ai

    CoverGen --> DeAPI1{"DeAPI (Flux)"}:::ai
    DeAPI1 -- Success --> ImageStorage["/assets/visuals/"]:::storage
    DeAPI1 -- Fallback/401 --> Pollinations1{"Pollinations AI"}:::ai
    Pollinations1 --> ImageStorage

    EntityGen --> DeAPI2{"DeAPI (Flux)"}:::ai
    DeAPI2 -- Success --> ImageStorage
    DeAPI2 -- Fallback/401 --> Pollinations2{"Pollinations AI"}:::ai
    Pollinations2 --> ImageStorage

    SceneGen --> Pollinations3{"Pollinations AI"}:::ai
    Pollinations3 --> ImageStorage

    %% --- Audio Generation Pipeline ---
    User -->|Clicks Audiobook/Podcast| AudioModal["Audio Picker Modal"]:::frontend
    AudioModal --> AudioDispatcher["Audio Generation Dispatcher"]:::process
    
    AudioDispatcher --> PodcastScript["Generate Podcast Script (Optional)"]:::ai
    PodcastScript --> Deepseek["Deepseek / Gemini LLM"]:::ai
    Deepseek -.->|Returns Script| TTSDispatcher["TTS Synthesis Dispatcher"]:::process
    AudioDispatcher -->|Raw Text| TTSDispatcher
    
    TTSDispatcher --> ProviderCheck{"Check Selected Provider"}:::process
    ProviderCheck -->|Deepgram| Deepgram["Deepgram API (Chunked)"]:::ai
    ProviderCheck -->|ElevenLabs| ElevenLabs["ElevenLabs API"]:::ai
    ProviderCheck -->|Pollinations| PollinationsTTS["Pollinations TTS API"]:::ai
    ProviderCheck -->|Fallback/Free| EdgeTTS["Edge-TTS (Inbuilt)"]:::ai
    
    Deepgram --> AudioStorage["/assets/audio/"]:::storage
    ElevenLabs --> AudioStorage
    PollinationsTTS --> AudioStorage
    EdgeTTS --> AudioStorage

    %% --- Final Output / Immersive Experience ---
    ImageStorage --> ImmersiveMode["Immersive Reader UI"]:::frontend
    AudioStorage --> ImmersiveMode
    ExtractedData --> ImmersiveMode
    
    User <-->|Views Story, Hears Audio, Sees Art| ImmersiveMode
    User -->|Export All| ZipService["Package as .zip"]:::process
    ZipService --> Download[("Download to Device")]:::storage
```

### Key Phases Breakdown

1. **Input & Extraction:** The system ingests files, extracts the raw text, and stores the metadata in a local SQLite database (`library.db`).
2. **Semantic Analysis:** The raw text is passed to an LLM (primarily Gemini Flash/Pro) which acts as the "brain". It breaks the story down into characters (entities), settings (scenes), and summaries.
3. **Visual Generation:** 
   - Uses the extracted entities to generate consistent character portraits.
   - Uses the scene descriptions and character data to generate matching scene backgrounds.
   - Defaults to **deAPI (Flux)** for high quality, with an automatic, safe fallback to **Pollinations AI** if the API key fails.
4. **Audio Generation:** The user selects a provider via the new dashboard modal. Large texts are intelligently chunked (e.g., for Deepgram's 2,000 character limit), processed into speech, and stitched together.
5. **Presentation:** Everything converges on the frontend. The Immersive Reader matches audio timestamps with scene images and text, creating a multimedia reading experience.
