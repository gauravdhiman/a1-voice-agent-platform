# Workflows

**See parent [SKILL.md](../SKILL.md) for overview and quickstart.**

## Workflow Overview

A workflow orchestrates agents, teams, and functions through defined steps for repeatable tasks. Output from each step flows to the next, creating a predictable pipeline.

## When to Use Workflows

Use a workflow when:
- You need predictable, repeatable execution
- Tasks have clear sequential steps with defined inputs/outputs
- You want audit trails and consistent results

Use a [team](teams.md) when you need flexible, collaborative problem-solving.

## Building Workflows

### Basic Workflow

```python
from agno.workflow import Workflow, Step
from agno.agent import Agent

researcher = Agent(name="Researcher", role="Gather information")
writer = Agent(name="Writer", role="Create content")

workflow = Workflow(
    name="Content Pipeline",
    steps=[
        Step(name="research", agent=researcher),
        Step(name="write", agent=writer),
    ],
)
```

### Running Workflows

```python
response = workflow.run("Write about AI trends")
print(response.content)
```

### Streaming Workflows

```python
for event in workflow.run("Write about AI", stream=True):
    print(event.content, end="", flush=True)
```

## Workflow Steps

### Agent Step

```python
Step(name="research", agent=researcher)
```

### Team Step

```python
research_team = Team(members=[agent1, agent2])

Step(name="analyze", team=research_team)
```

### Function Step

```python
def process_data(data: str) -> str:
    """Process workflow data."""
    return f"Processed: {data}"

Step(name="process", function=process_data)
```

## Workflow Patterns

### Sequential Workflow

```python
workflow = Workflow(
    name="Sequential",
    steps=[
        Step(name="research", agent=researcher),
        Step(name="summarize", agent=summarizer),
        Step(name="write", agent=writer),
    ],
)
```

**Use when:** Each step depends on previous step's output

### Parallel Workflow

```python
from agno.workflow import Step, Workflow
from agno.workflow.types import Parallel

workflow = Workflow(
    name="Parallel Research",
    steps=[
        Parallel(steps=[
            Step(name="news_research", agent=news_agent),
            Step(name="finance_research", agent=finance_agent),
        ]),
        Step(name="synthesize", agent=summarizer),
    ],
)
```

**Use when:** Multiple independent tasks can run simultaneously

### Conditional Workflow

```python
from agno.workflow import Condition

def needs_fact_check(step_input: StepInput) -> bool:
    """Check if fact-checking needed."""
    content = step_input.previous_step_content or ""
    return any(word in content.lower() for word in ["study shows", "research"])

workflow = Workflow(
    name="Conditional Research",
    steps=[
        Step(name="research", agent=researcher),
        Condition(
            name="fact_check_condition",
            evaluator=needs_fact_check,
            steps=[
                Step(name="fact_check", agent=fact_checker),
            ],
        ),
        Step(name="write", agent=writer),
    ],
)
```

**Use when:** Next steps depend on evaluation of current results

### Loop Workflow

```python
from agno.workflow import Loop

workflow = Workflow(
    name="Iterative Research",
    steps=[
        Step(name="initial_research", agent=researcher),
        Loop(
            name="refine_loop",
            max_iterations=3,
            steps=[
                Step(name="analyze", agent=analyzer),
                Step(name="refine", agent=refiner),
            ],
        ),
        Step(name="finalize", agent=writer),
    ],
)
```

**Use when:** Task requires iterative refinement

### Router Workflow

```python
from agno.workflow import Router

def route_task(step_input: StepInput) -> str:
    """Route to appropriate step."""
    query = step_input.run_input or ""
    if "finance" in query.lower():
        return "financial_analysis"
    elif "tech" in query.lower():
        return "tech_analysis"
    return "general_analysis"

workflow = Workflow(
    name="Routing Workflow",
    steps=[
        Router(
            name="task_router",
            selector=route_task,
            routes={
                "financial_analysis": Step(name="finance", agent=finance_agent),
                "tech_analysis": Step(name="tech", agent=tech_agent),
                "step_name": "general_analysis": Step(name="general", agent=general_agent),
            },
        ),
    ],
)
```

**Use when:** Different paths based on input

## Workflow Configuration

### Common Parameters

| Parameter           | Type   | Description                           |
| ------------------ | ------ | ------------------------------------- |
| `name`              | str    | Workflow name                          |
| `steps`             | list   | Ordered list of steps                  |
| `description`        | str    | Workflow description                   |
| `model`             | Model  | Model for workflow (if needed)      |
| `db`                | Db     | Database for persistence              |
| `session_state`     | dict   | Initial session state                 |

### Step Parameters

| Parameter           | Type    | Description                       |
| ------------------ | ------- | --------------------------------- |
| `name`              | str     | Step name                         |
| `agent`             | Agent   | Agent to execute (optional)         |
| `team`              | Team    | Team to execute (optional)          |
| `function`          | callable| Function to execute (optional)       |
| `description`        | str     | Step description                  |
| `input`             | dict    | Input data for step (optional)     |

### Condition Parameters

| Parameter           | Type     | Description                     |
| ------------------ | -------- | ------------------------------- |
| `name`              | str      | Condition name               |
| `evaluator`         | callable | Function returning bool       |
| `steps`             | list     | Steps to execute if True     |

### Loop Parameters

| Parameter           | Type   | Description                        |
| ------------------ | ------ | ---------------------------------- |
| `name`              | str    | Loop name                          |
| `max_iterations`    | int    | Maximum loop iterations             |
| `steps`             | list   | Steps to execute in loop           |

### Router Parameters

| Parameter           | Type     | Description                         |
| ------------------ | -------- | ----------------------------------- |
| `name`              | str      | Router name                     |
| `selector`          | callable | Function returning route key       |
| `routes`            | dict     | Mapping of keys to steps         |

## Workflow Patterns

### Content Creation Pipeline

```python
researcher = Agent(
    name="Researcher",
    role="Gather comprehensive information",
    tools=[HackerNewsTools(), YFinanceTools()],
)

planner = Agent(
    name="Content Planner",
    role="Plan content schedule",
    instructions=["Plan 3 posts per week", "Ensure variety"],
)

creator = Agent(
    name="Content Creator",
    role="Write engaging content",
    instructions=["Be creative", "Use markdown"],
)

content_workflow = Workflow(
    name="Content Pipeline",
    steps=[
        Step(name="research", agent=researcher),
        Step(name="plan", agent=planner),
        Step(name="create", agent=creator),
    ],
)
```

### Research and Fact-Checking

```python
def needs_fact_check(step_input: StepInput) -> bool:
    """Check if claims need verification."""
    content = step_input.previous_step_content or ""
    fact_indicators = ["study shows", "research", "data shows"]
    return any(indicator in content.lower() for indicator in fact_indicators)

workflow = Workflow(
    name="Verified Research",
    steps=[
        Step(name="research", agent=researcher),
        Condition(
            name="fact_check",
            evaluator=needs_fact_check,
            steps=[
                Step(name="verify", agent=fact_checker),
            ],
        ),
        Step(name="summarize", agent=summarizer),
    ],
)
```

### Multi-Analysis Workflow

```python
from agno.workflow.types import Parallel

workflow = Workflow(
    name="Multi-Analysis",
    steps=[
        Step(name="collect_data", agent=collector),
        Parallel(steps=[
            Step(name="sentiment_analysis", agent=sentiment_analyst),
            Step(name="topic_analysis", agent=topic_analyst),
            Step(name="trend_analysis", agent=trend_analyst),
        ]),
        Step(name="synthesize", agent=summarizer),
    ],
)
```

### Customer Support Workflow

```python
classifier = Agent(name="Classifier", role="Categorize issue")
billing_agent = Agent(name="Billing", role="Handle billing issues")
technical_agent = Agent(name="Technical", role="Handle technical issues")
closer = Agent(name="Closer", role="Close ticket with resolution")

workflow = Workflow(
    name="Support Workflow",
    steps=[
        Step(name="classify", agent=classifier),
        Router(
            name="route",
            selector=lambda si: si.output.get("category", "general"),
            routes={
                "billing": Step(name="handle_billing", agent=billing_agent),
                "technical": Step(name="handle_technical", agent=technical_agent),
                "step_name": "general": Step(name="handle_general", agent=general_agent),
            },
        ),
        Step(name="close", agent=closer),
    ],
)
```

## Workflow Execution Control

### Access Previous Step Output

```python
def process_step(step_input: StepInput) -> str:
    """Access output from previous step."""
    previous_content = step_input.previous_step_content or ""
    return f"Processing: {previous_content}"
```

### Access Multiple Previous Steps

```python
def process_step(step_input: StepInput) -> str:
    """Access outputs from multiple previous steps."""
    research_output = step_input.steps_outputs.get("research", {})
    analysis_output = step_input.steps_outputs.get("analysis", {})
    return f"Research: {research_output}, Analysis: {analysis_output}"

workflow = Workflow(
    steps=[
        Step(name="research", agent=researcher),
        Step(name="analysis", agent=analyst),
        Step(name="synthesize", function=process_step),
    ],
)
```

### Workflow Cancellation

```python
# In workflow execution
response = workflow.run("Process data")

# Cancel if needed
workflow.cancel_run(run_id=response.run_id)
```

### Conversational Workflows

```python
from agno.workflow import Workflow, Step

workflow = Workflow(
    name="Conversational Workflow",
    conversational=True,  # Enable chat interaction
    steps=[
        Step(name="step1", agent=agent1),
        Step(name="step2", agent=agent2),
    ],
)

# User can now chat with workflow
response = workflow.run("Start conversation")
```

## Event Types

**Core events:**
- `WorkflowStarted` - Workflow execution started
- `StepStarted` - Step execution started
- `StepCompleted` - Step execution completed
- `WorkflowCompleted` - Workflow execution completed
- `WorkflowError` - Error occurred
- `WorkflowCancelled` - Workflow was cancelled

**Condition events:**
- `ConditionExecutionStarted` - Condition evaluation started
- `ConditionExecutionCompleted` - Condition evaluation completed

## Workflow with State

```python
workflow = Workflow(
    name="Stateful Workflow",
    session_state={"counter": 0, "results": []},
    steps=[
        Step(name="step1", agent=agent1),
        Step(name="step2", agent=agent2),
    ],
)
```

Access state in function:

```python
def process_step(step_input: StepInput) -> str:
    """Access workflow state."""
    counter = step_input.session_state.get("counter", 0)
    step_input.session_state["counter"] = counter + 1
    return f"Step {counter}"
```

## See Also

- [Agents](agents.md) - Single agent patterns
- [Teams](teams.md) - Multi-agent coordination
- [Workflow Examples](../cookbook/workflows.md) - Example workflows
