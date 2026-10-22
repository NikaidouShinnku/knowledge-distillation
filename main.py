
import json
import shutil

import pyperclip
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.history import FileHistory

from agent.critique import CritiqueAgent
from agent.generation_review import ReviewGenerationAgent
from agent.simulation import SimulationAgent
from agent.summary import SummaryAgent
from agent.entity_extraction_distill import EntityExtractionAgent
from knowledge_graph.entity_relation_triple import EntityRelationTriple
from chat_history import ChatHistory
from common.show_utils import show_response, to_progress_bar
from knowledge_graph.model import KnowledgeGraph
from knowledge_graph.model_manager import KnowledgeTreeManager
import argparse
from llms.statistics import get_usage
from llms import default_model, ModelConfig, ModelClient, ConfigurationError, ModelAPIError
import subprocess
from plan import plan_directory
from agent.distill import DistillAgent
from agent.generation import GenerationAgent
from progress.progress import Progress
from prompts import read_prompt
from tts import tts
from common.setup import select_expert, select_topic, select_tone
from common.show_utils import processing

from common.mermaid_code import generate_mermaid
def hello():
    print("Knowledge Distillation Expert Agent")


def dump(file: str, description: str, knowledge_graph, chat_history, current_response: str):
    """
    Write the chat history, current response and knowledge tree to a JSON file.
    Args:
        file (str): The path to the JSON file where the data will be saved.
        description (str): Description of the knowledge tree.
        knowledge_graph: The knowledge graph data.
        chat_history: The chat history data.
        current_response (str): The current response data.
    """

    data = {
        "description": description,
        "knowledge_graph": knowledge_graph,
        "chat_history": chat_history,
        "current_response": current_response,
        "reason": "",
        "target_objective": "",
        "question": ""
    }


    with open(file + ".template", 'a') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")

def dump_snapshot(
        file: str,
        knowledge_graph,
        chat_history,
        review_history,
        interviewee,
        model,
        task,
        tone,
        progress,
        entity_graph=None
):
    data = {
        'knowledge_graph': knowledge_graph,
        'chat_history': chat_history,
        'review_history': review_history,
        'interviewee': interviewee,
        'model': model,
        'task': task,
        'tone': tone,
        'progress': progress,
        'entity_graph': entity_graph
    }
    with open(file + ".json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_restore_data(file: str):
    with open("snapshot/" + file + ".json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        if data.get("entity_graph"):
            entity_relationship_triple.__dict__.update(data["entity_graph"])
        task = data["task"]
        interviewee = data["interviewee"]
        model = data["model"]
        distilled_tree = KnowledgeGraph(**data["knowledge_graph"])
        chat_history = ChatHistory(**data["chat_history"])
        review_history = ChatHistory(**data["review_history"])
        tone = data["tone"]
        progress = Progress(total_minutes=0,objectives_count=0)
        progress.load_from_dict(data["progress"])
    return distilled_tree, chat_history, review_history, task, interviewee, model, tone, progress

def show_progress():
    progress_template = read_prompt("show_progress")
    p = progress.get_progress()
    usage = get_usage()

    objective_progress = to_progress_bar(
        n_done=int(p["progress_completed"] * 100),
        n_total=p["objectives_total"] * 100
    )
    time_elapsed = p["time_total"] - p["time_remaining"]
    time_progress = to_progress_bar(
        n_done=time_elapsed,
        n_total=p["time_total"]
    )
    progress_stats = progress_template.format(
        time_progress=time_progress,
        time_elapsed=time_elapsed,
        time_total=p["time_total"],
        obj_progress=objective_progress,
        obj_completed=p["objectives_completed_count"],
        obj_total=p["objectives_total"],
        rounds_completed=p["round_total"],
        rounds_remaining=p["rounds_remaining"] if p["rounds_remaining"] != 'Unknown' else '?',
        prompt_tokens = usage['prompt_tokens'],
        completion_tokens = usage['completion_tokens'],
        total_tokens = usage['total_tokens'],
        price='未配置计价，请以供应商账单为准'
    )
    show_response(progress_stats, title="访谈进度概览", width=80)

def show_tree():
    from knowledge_graph.style import build_rich_tree
    from rich.console import Console
    tree = tree_manager.get_current_tree()
    if not tree:
        return
    styled_tree = build_rich_tree(tree)
    console = Console()
    console.print(styled_tree)


def show_graph():
    try:
        from entity_extraction.mermaid_opts import create_mermaid_png_and_display
        mermaid_code = generate_mermaid(entity_relationship_triple.get_entities(),
                                       entity_relationship_triple.get_relationships())
        create_mermaid_png_and_display(mermaid_code=mermaid_code,
                                      relationships=entity_relationship_triple.get_relationships())
    except (ImportError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Graph unavailable: {exc}. Install optional dependencies, mmdc and WezTerm.")

if __name__ == '__main__':
    from common.io import configure_console
    configure_console()
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default=None, type=str, help='Model name')
    parser.add_argument('--evaluate', action='store_true', help='Evaluate each answer with an extra model call')
    parser.add_argument('--graph', action='store_true', help='Render graph with Mermaid CLI and WezTerm')
    parser.add_argument('--stream', action=argparse.BooleanOptionalAction, default=True, help='Stream interviewer replies')
    parser.add_argument('--task', type=str, help='Skip the topic menu and use this plan')
    parser.add_argument('--interviewee', type=str, help='Skip the expert menu and use this profile')
    parser.add_argument('--prompt-language', choices=['en-US', 'zh-CN'], default='en-US', help='Prompt and style language')
    parser.add_argument('--entities', action='store_true', help='Extract entity relationships with an extra model call')
    parser.add_argument('--auto', action='store_true', help='Do a simulation')
    parser.add_argument('--tts', action='store_true', help='Enable tts')
    parser.add_argument('--restore', type=str, help='restore the task', default="")
    parser.add_argument('--generation-mode', type=str, choices=["conversation", "solo"], help='Use conversation for group discussion or solo for speed', default="conversation")
    args = parser.parse_args()

    from pathlib import Path
    import os
    os.chdir(Path(__file__).resolve().parent)
    Path("snapshot").mkdir(exist_ok=True)
    Path("task_result").mkdir(exist_ok=True)
    hello()
    os.environ['PROMPT_LANGUAGE'] = args.prompt_language
    if not args.restore:
        args.interviewee = args.interviewee or select_expert()
        args.task = args.task or select_topic()

    tone = None
    entity_relationship_triple = EntityRelationTriple()
    tree_manager = KnowledgeTreeManager()
    chat_history = ChatHistory()
    review_history = ChatHistory()
    if not args.restore:
        distilled_tree = KnowledgeGraph.restore(f"{plan_directory()}/{args.task}")
        progress = Progress(total_minutes=distilled_tree.estimated_minute, objectives_count=len(distilled_tree.objectives))

    requested_model = args.model
    if args.restore:
        (distilled_tree,
         chat_history,
         review_history,
         args.task,
         args.interviewee,
         args.model,
         tone,
         progress) = load_restore_data(args.restore)

    args.model = requested_model or args.model or default_model()
    ModelConfig.resolve(args.model)
    tree_manager.push_back(distilled_tree)

    if not tone:
        tone = select_tone(args.prompt_language)
    print(f"Model: {args.model} | Prompts: {args.prompt_language} | Mode: {args.generation_mode}")
    if args.generation_mode == 'solo':
        print("Fast interview: knowledge updates and questions. Use --generation-mode conversation for question review.")
    distill_agent = DistillAgent(
        name=args.task+"-distill-agent",
        distilled_tree=distilled_tree,
        chat_history=chat_history,
        interviewee=args.interviewee,
        model=args.model
    )
    entity_extraction_agent = EntityExtractionAgent(
        name=args.task+"-distill-agent",
        distilled_tree=distilled_tree,
        chat_history=chat_history,
        model=args.model,
        entity_types=["ANIMAL", "SUBSTANCE", "DATE", "EVENT", "TRAITS", "ACTION", "HABITS", "OTHER"],
        entity_relationship_triple=entity_relationship_triple
    )
    generate_agent = GenerationAgent(
        name=args.task+"-generate-agent",
        distilled_tree=distilled_tree,
        chat_history=chat_history,
        interviewee=args.interviewee,
        model=args.model,
        progress=progress,
        tone=tone,
        review_history=review_history
    )
    simulate_agent = SimulationAgent(
        name=args.task+"-simulate-agent",
        distilled_tree=distilled_tree,
        chat_history=chat_history,
        interviewee=args.interviewee,
        model=args.model
    )
    critique_agent = CritiqueAgent(
        name=args.task+"-critique-agent",
        distilled_tree=distilled_tree,
        chat_history=chat_history,
        interviewee=args.interviewee,
        model=args.model
    )
    summary_agent = SummaryAgent(
        name=args.task + "-summary-agent",
        distilled_tree=distilled_tree,
        chat_history=chat_history,
        model=args.model
    )
    review_generation_agent = ReviewGenerationAgent(
        name=args.task+"-review-generate-agent",
        distilled_tree=distilled_tree,
        model=args.model,
        progress=progress,
        review_history=review_history
    )
    agent_group = [distill_agent, entity_extraction_agent, generate_agent, simulate_agent, critique_agent, summary_agent, review_generation_agent]

    turn = 0
    term_col, _ = shutil.get_terminal_size()
    while True:

        question = None
        if args.generation_mode == "conversation":
            approved = False
            for i in range(5):
                with processing("Drafting question"):
                    question = generate_agent.generate_question(stream=args.stream)
                    question = show_response(question, title="Question proposer / Group discussion", offset=term_col//2,width=60, title_align="right", border_color="blue")
                review_history.append(role="Asker", content=question)
                with processing("Reviewing question"):
                    verification, answer = review_generation_agent.generate_review()
                if verification.strip().lower() != "yes":
                    review_history.append(role="Reviewer", content=answer)
                    show_response("[REVISE]\n"+answer, title="Question reviewer / Group discussion", offset=term_col//2, width=60, title_align="left", border_color="blue")
                if verification.strip().lower() == "yes":
                    approved = True
                    review_history.append(role="Reviewer", content="该问题被审核通过")
                    show_response("[OK] " + (answer.strip() or "Approved for the interview."), title="Question reviewer / Group discussion", offset=term_col // 2, width=60, title_align="left", border_color="blue")
                    break
            if not approved:
                print("问题连续五次未通过审核，访谈停止；已有知识树已保留。")
                break
        else:
            with processing("Preparing question"):
                question = generate_agent.generate_question(stream=args.stream)
                question = show_response(res=question, title='Interviewer', title_align="right")
                review_history.append(role="Asker", content=question)

        if args.generation_mode == 'conversation':
            question = show_response(res=question, title='Interviewer', title_align="right")
        chat_history.append(role="萃取专家", content=question)
        if args.tts:
            try:
                tts(question, output="question.mp3", play=True)
            except (ImportError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
                print(f"TTS unavailable: {exc}; continuing with text")
        if args.auto:
            user_input = simulate_agent.simulate_response()
            show_response(user_input, title="Expert (simulation)", title_align='left')
            turn += 1
        else:
            try:
                session = PromptSession(
                    HTML('<ansicyan><b>{} &gt;&gt; </b></ansicyan>').format(generate_agent.interviewee_name),
                    history=FileHistory('history.txt')
                )
                while True:
                    user_input = session.prompt()
                    if user_input in ("/quit", "/exit"):
                        raise SystemExit(0)
                    elif user_input == "/dump":
                        chat_history_chopped_last = ChatHistory()
                        chat_history_chopped_last.chat_history = chat_history.chat_history[:-1]
                        dump_snapshot(
                            file="snapshot/test-snapshot2",
                            knowledge_graph=distilled_tree.model_dump(),
                            chat_history=chat_history_chopped_last.model_dump(),
                            review_history=review_history.model_dump(),
                            interviewee=args.interviewee,
                            model=args.model,
                            task=args.task,
                            tone=tone,
                            progress=progress.mapping(),
                            entity_graph=entity_relationship_triple.__dict__,
                        )
                    elif user_input == "/auto":
                        args.auto = True
                        user_input = simulate_agent.simulate_response()
                        show_response(user_input, title="Expert (simulation)", title_align='left')
                        turn += 1
                        break
                    elif user_input.startswith("/model "):
                        selected = user_input.split(maxsplit=1)[1].strip()
                        try:
                            ModelConfig.resolve(selected)
                            args.model = selected
                            for selected_agent in agent_group:
                                selected_agent.model = selected
                            print(f"Model: {selected}")
                        except ConfigurationError as exc:
                            print(str(exc))
                    elif user_input == "/model":
                        print(f"Model: {args.model}")
                    elif user_input.startswith("/models "):
                        provider = user_input.split(maxsplit=1)[1].strip()
                        try:
                            with ModelClient(ModelConfig.resolve(f"{provider}/_")) as client:
                                print("\n".join(client.models()))
                        except (ConfigurationError, ModelAPIError) as exc:
                            print(str(exc))
                    elif user_input == "/tree":
                        show_tree()
                    elif user_input == "/graph":
                        show_graph()
                    elif user_input == "/generation-prompt":
                        show_response(generate_agent.get_prompt(), title="Generation / Prompt")
                    elif user_input == "/distill-prompt":
                        show_response(distill_agent.get_prompt(), title="Distill / Prompt")
                    elif user_input == "/review-generation-prompt":
                        show_response(review_generation_agent.get_prompt(), title="Generation-Review / Prompt")
                    elif user_input == "/summary-prompt":
                        show_response(summary_agent.get_prompt(), title="Summary / Prompt")
                    elif user_input == "/refine":
                        summary_agent.restructure(turn=progress.get_round())
                        tree_manager.push_back(distilled_tree.clone())
                        progress.objectives_completed = distilled_tree.get_completed_objective_num()
                        progress.total_objective_progress = distilled_tree.get_total_objective_progress()
                        distilled_tree.dump("task_result/current_distilled_tree")
                    elif user_input == "/undo":
                        restored = tree_manager.undo()
                        if restored is not None:
                            distilled_tree.__dict__.update(restored.model_copy(deep=True).__dict__)
                            progress.objectives_completed = distilled_tree.get_completed_objective_num()
                            progress.total_objective_progress = distilled_tree.get_total_objective_progress()
                            distilled_tree.dump("task_result/current_distilled_tree")
                    elif user_input == "/redo":
                        restored = tree_manager.redo()
                        if restored is not None:
                            distilled_tree.__dict__.update(restored.model_copy(deep=True).__dict__)
                            progress.objectives_completed = distilled_tree.get_completed_objective_num()
                            progress.total_objective_progress = distilled_tree.get_total_objective_progress()
                            distilled_tree.dump("task_result/current_distilled_tree")
                    elif user_input == "/progress":
                        show_progress()
                    elif user_input == '/asr':
                        try:
                            from asr import record_and_asr
                            user_input = record_and_asr()
                        except (ImportError, OSError, RuntimeError) as exc:
                            print(f'ASR unavailable: {exc}; enter a text answer')
                            continue
                        if user_input and user_input.strip():
                            show_response(res=user_input, title="ASR Result", title_align="left", width=40)
                            break
                        continue
                    elif user_input == '/clipboard':
                        user_input = pyperclip.paste()
                        if user_input:
                            break

                    elif user_input[:1] == "/":
                        print("Unknown Command")
                        continue
                    elif user_input:
                        break
            finally:
                    pass


        chat_history.append(role=args.interviewee, content=user_input)
        if args.entities or args.graph:
            try:
                with processing("Extracting entity relationships"):
                    entity_extraction_agent.extract_triplet(turn=progress.get_round())
            except (ValueError, ModelAPIError) as exc:
                print(f"关系抽取失败，继续更新知识树: {exc}")
        if args.graph:
            show_graph()

        with processing("Updating knowledge tree"):
            distill_agent.update_tree(turn=progress.get_round())
        tree_manager.push_back(distilled_tree)
        if args.evaluate:
            critique_agent.rate_response()
        progress.on_interviewee_replied(
            objectives_completed=distilled_tree.get_completed_objective_num(),
            total_objective_progress=distilled_tree.get_total_objective_progress()
        )

        if progress.get_time_remaining() <= 0:
            show_tree()
            if args.graph:
                show_graph()
            show_progress()
            with processing("Preparing closing summary"):
                show_response(res=generate_agent.end_chat(), title='Interviewer', title_align="right")
            break
        if args.auto:
            if turn % 3 == 0:
                verified = input("continue?(Y/N)")
                if verified in ('Y', ''):
                    continue
                else:
                    args.auto = False


