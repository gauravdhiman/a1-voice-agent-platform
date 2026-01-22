#!/bin/bash

# Mermaid Diagram Template Generator
# This script generates templates for common mermaid diagram types

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Show usage information
usage() {
    echo -e "${BLUE}Mermaid Diagram Template Generator${NC}"
    echo ""
    echo "Usage: $0 <diagram-type> [output-file]"
    echo ""
    echo "Diagram Types:"
    echo "  flowchart    - Process flow or decision tree"
    echo "  sequence     - Sequence diagram for interactions"
    echo "  er           - Entity-Relationship diagram"
    echo "  class        - Class diagram for OOP"
    echo "  state        - State machine diagram"
    echo "  gantt        - Project timeline"
    echo "  pie          - Data visualization pie chart"
    echo "  journey      - User experience journey"
    echo "  gitgraph     - Git branching diagram"
    echo "  mindmap      - Mind map diagram"
    echo ""
    echo "Examples:"
    echo "  $0 flowchart my-process.md"
    echo "  $0 sequence > diagram.md"
    echo "  $0 er database-schema.md"
}

# Generate flowchart template
generate_flowchart() {
    cat << 'EOF'
```mermaid
flowchart TD
    %% Define nodes
    A[Start] --> B{Decision Point}
    B -->|Yes| C[Process 1]
    B -->|No| D[Process 2]
    C --> E[End]
    D --> E

    %% Styling (optional)
    classDef processClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef decisionClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef endClass fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px

    class A,C,D processClass
    class B decisionClass
    class E endClass
```
EOF
}

# Generate sequence diagram template
generate_sequence() {
    cat << 'EOF'
```mermaid
sequenceDiagram
    participant User
    participant System
    participant Database

    User->>System: Request Action
    System->>Database: Query Data
    Database-->>System: Return Results
    System-->>User: Display Response

    %% Notes
    Note over User,System: User initiates the process
    Note right of System: System processes the request
```
EOF
}

# Generate ER diagram template
generate_er() {
    cat << 'EOF'
```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER {
        string name
        string custNumber
        string sector
    }
    ORDER {
        int orderNumber
        string deliveryAddress
    }
    LINE-ITEM {
        string productCode
        int quantity
        float pricePerUnit
    }
```
EOF
}

# Generate class diagram template
generate_class() {
    cat << 'EOF'
```mermaid
classDiagram
    Animal <|-- Duck
    Animal <|-- Fish
    Animal <|-- Zebra
    Animal : +int age
    Animal : +String gender
    Animal: +isMammal()
    Animal: +mate()
    class Duck{
        +String beakColor
        +swim()
        +quack()
    }
    class Fish{
        -int sizeInFeet
        -canEat()
    }
    class Zebra{
        +bool is_wild
        +run()
    }
```
EOF
}

# Generate state diagram template
generate_state() {
    cat << 'EOF'
```mermaid
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]

    %% Notes
    note right of Still : This is a note
    note left of Crash : This is another note
```
EOF
}

# Generate Gantt chart template
generate_gantt() {
    cat << 'EOF'
```mermaid
gantt
    title A Gantt Diagram
    dateFormat  YYYY-MM-DD
    section Section
    A task           :a1, 2014-01-01, 30d
    Another task     :after a1  , 20d
    section Another
    Task in sec      :2014-01-12  , 12d
    another task      : 24d
```
EOF
}

# Generate pie chart template
generate_pie() {
    cat << 'EOF'
```mermaid
pie title Pets adopted by volunteers
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15
```
EOF
}

# Generate user journey template
generate_journey() {
    cat << 'EOF'
```mermaid
journey
    title My working day
    section Go to work
      Make tea: 5: Me
      Go upstairs: 3: Me
      Do work: 1: Me, Cat
    section Go home
      Go downstairs: 5: Me
      Sit down: 5: Me
```
EOF
}

# Generate gitgraph template
generate_gitgraph() {
    cat << 'EOF'
```mermaid
gitgraph
    commit id: "Initial commit"
    branch develop
    checkout develop
    commit id: "Add feature"
    checkout main
    merge develop
    commit id: "Release"
```
EOF
}

# Generate mindmap template
generate_mindmap() {
    cat << 'EOF'
```mermaid
mindmap
  root((mindmap))
    Origins
      Long history
      ::icon(fa fa-book)
      Popularisation
        British popular psychology author Tony Buzan
    Research
      On effectiveness<br/>and features
      On Automatic creation
        Uses
            Creative techniques
            Strategic planning
            Argument mapping
    Tools
      Pen and paper
      Mermaid
```
EOF
}

# Main function
main() {
    if [ $# -lt 1 ]; then
        usage
        exit 1
    fi

    local diagram_type="$1"
    local output_file="$2"

    case "$diagram_type" in
        flowchart|flow)
            generate_flowchart
            ;;
        sequence|seq)
            generate_sequence
            ;;
        er|erdiagram)
            generate_er
            ;;
        class|classdiagram)
            generate_class
            ;;
        state|statediagram)
            generate_state
            ;;
        gantt)
            generate_gantt
            ;;
        pie)
            generate_pie
            ;;
        journey)
            generate_journey
            ;;
        gitgraph|git)
            generate_gitgraph
            ;;
        mindmap|mind)
            generate_mindmap
            ;;
        *)
            echo -e "${RED}Error: Unknown diagram type '$diagram_type'${NC}"
            echo ""
            usage
            exit 1
            ;;
    esac

    if [ -n "$output_file" ]; then
        echo -e "${GREEN}Template generated and saved to: $output_file${NC}"
    else
        echo -e "${GREEN}Template generated. Copy and paste into your markdown file.${NC}"
    fi
}

main "$@"
