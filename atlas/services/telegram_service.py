"""Telegram bot service for Heimdall."""
import os
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from atlas.db.session import get_session
from atlas.services.groq_service import chat as groq_chat
from atlas.services.budget_service import (
    add_transaction,
    list_budget_categories,
    create_budget_category,
    get_monthly_summary,
)
from atlas.core.indexer import run_indexer


def convert_markdown_tables_to_text(text: str) -> str:
    """Convert markdown tables to simple text format for Telegram."""
    import re
    
    # Pattern to match markdown tables
    table_pattern = r'(\|.*?\|\n)+'
    
    def replace_table(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')
        
        # Skip separator lines (|---|---|)
        data_lines = [line for line in lines if '---' not in line]
        
        if not data_lines:
            return table_text
        
        # Parse table data
        rows = []
        for line in data_lines:
            # Remove leading/trailing pipes and split
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            rows.append(cells)
        
        # Find max column width for formatting
        if not rows:
            return table_text
        
        max_cols = max(len(row) for row in rows)
        col_widths = [0] * max_cols
        
        for row in rows:
            for i, cell in enumerate(row):
                if i < max_cols:
                    col_widths[i] = max(col_widths[i], len(cell))
        
        # Build text table
        result = []
        for i, row in enumerate(rows):
            # Pad row to max columns
            padded_row = row + [''] * (max_cols - len(row))
            # Format each cell
            formatted_cells = []
            for j, cell in enumerate(padded_row):
                formatted_cells.append(cell.ljust(col_widths[j]))
            result.append(' | '.join(formatted_cells))
            # Add separator after header
            if i == 0:
                separator = ' | '.join(['-' * w for w in col_widths])
                result.append(separator)
        
        return '\n'.join(result)
    
    # Replace all tables
    return re.sub(table_pattern, replace_table, text)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")

# Conversation states for expense form
EXPENSE_AMOUNT, EXPENSE_DESCRIPTION, EXPENSE_CATEGORY, EXPENSE_PAYMENT_METHOD, EXPENSE_MERCHANT, EXPENSE_DATE, EXPENSE_CONFIRM = range(7)

# Conversation states for income form
INCOME_AMOUNT, INCOME_DESCRIPTION, INCOME_CATEGORY, INCOME_SOURCE, INCOME_DATE, INCOME_CONFIRM = range(6)

# Temporary storage for form data
expense_forms: Dict[int, Dict[str, Any]] = {}
income_forms: Dict[int, Dict[str, Any]] = {}

# Chat history storage per user
chat_history: Dict[int, list[dict]] = {}


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized to use the bot."""
    return str(user_id) == TELEGRAM_USER_ID


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return
    
    welcome_text = """
🤖 *Welcome to Heimdall*

Your personal AI assistant is now available on Telegram!

**Quick Actions:**
💬 Chat with me directly
💰 Add income/expense
🎯 Manage goals
📚 Search your memory
📋 Daily brief

**Commands:**
/chat - Chat with Heimdall
/brief - Get daily brief
/goals - Manage goals
/search - Search memory
/vault - Browse vault
/income - Add income
/expense - Add expense
/budget - Budget summary
/help - Show this message
    """
    
    keyboard = [
        [InlineKeyboardButton("💬 Chat", callback_data="chat"),
         InlineKeyboardButton("💰 Add Expense", callback_data="add_expense")],
        [InlineKeyboardButton("💵 Add Income", callback_data="add_income"),
         InlineKeyboardButton("🎯 Goals", callback_data="goals")],
        [InlineKeyboardButton("📚 Search Memory", callback_data="search"),
         InlineKeyboardButton("📋 Daily Brief", callback_data="brief")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return
    
    help_text = """
🤖 *Heimdall Commands*

**Chat & Memory:**
/chat - Chat with Heimdall (shared context with web)
/search <query> - Search your memory
/vault - Browse vault notes

**Daily:**
/brief - Get your daily brief

**Goals & Habits:**
/goals - List and manage goals

**Budget:**
/income - Add income
/expense - Add expense
/budget - Monthly budget summary
/can_afford <amount> - Check if you can afford

**Other:**
/help - Show this message
    """
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular chat messages."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return

    user_message = update.message.text
    user_id_int = update.effective_user.id
    user_id = str(user_id_int)

    # Show typing indicator
    await update.message.chat.send_action("typing")

    try:
        # Build messages for LLM
        from atlas.core.personality import get_system_prompt
        from atlas.db.vector_store import search

        # Get or initialize chat history for this user
        if user_id_int not in chat_history:
            chat_history[user_id_int] = []

        # Search for relevant context
        async with get_session() as session:
            context_results = await search("vector_memory", user_message, limit=3)
            context_text = "\n".join(f"- {r['text']}" for r in context_results) if context_results else ""

            system_prompt = get_system_prompt(context=context_text, with_memory=bool(context_results))

            # Build messages with history (last 10 messages)
            history = chat_history[user_id_int][-10:]
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})

            # Call groq service for chat completion
            response = await groq_chat(messages, model="groq-llama4-scout")

            # Convert markdown tables to text format for Telegram
            response = convert_markdown_tables_to_text(response)

            # Send response with markdown parsing (tables are now converted to text)
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

            # Update chat history
            chat_history[user_id_int].append({"role": "user", "content": user_message})
            chat_history[user_id_int].append({"role": "assistant", "content": response})

            # Keep history manageable (max 20 messages)
            if len(chat_history[user_id_int]) > 20:
                chat_history[user_id_int] = chat_history[user_id_int][-20:]

            # Store in memory and trigger auto-indexer
            from atlas.db.vector_store import store
            await store("vector_memory", user_message, source_type="telegram", source_path="telegram")
            await run_indexer(user_message, response)

    except Exception as e:
        await update.message.reply_text(f"Sorry, something went wrong: {str(e)}")


async def brief_command_from_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Handle /brief command from callback."""
    if not is_authorized(query.from_user.id):
        await query.message.reply_text("Sorry, you're not authorized to use this bot.")
        return

    await query.message.chat.send_action("typing")

    try:
        async with get_session() as session:
            from atlas.api.brief import generate_brief
            brief = await generate_brief(session, str(query.from_user.id))
            await query.message.reply_text(brief, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await query.message.reply_text(f"Sorry, couldn't generate brief: {str(e)}")


async def brief_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /brief command."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return

    await update.message.chat.send_action("typing")

    try:
        async with get_session() as session:
            from atlas.api.brief import generate_brief
            brief = await generate_brief(session, str(update.effective_user.id))
            await update.message.reply_text(brief, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Sorry, couldn't generate brief: {str(e)}")


async def budget_command_from_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Handle /budget command from callback."""
    if not is_authorized(query.from_user.id):
        await query.message.reply_text("Sorry, you're not authorized to use this bot.")
        return

    await query.message.chat.send_action("typing")

    try:
        async with get_session() as session:
            summary = await get_monthly_summary(session, str(query.from_user.id))

            budget_text = f"""
📊 *Monthly Budget Summary*

*Income:* ${summary['income']:.2f}
*Expenses:* ${summary['expenses']:.2f}
*Net:* ${summary['net']:.2f}

*Transactions:* {summary['transaction_count']}
            """

            await query.message.reply_text(budget_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await query.message.reply_text(f"Sorry, couldn't get budget: {str(e)}")


async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /budget command."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return

    await update.message.chat.send_action("typing")

    try:
        async with get_session() as session:
            summary = await get_monthly_summary(session, str(update.effective_user.id))

            budget_text = f"""
📊 *Monthly Budget Summary*

*Income:* ${summary['income']:.2f}
*Expenses:* ${summary['expenses']:.2f}
*Net:* ${summary['net']:.2f}

*Transactions:* {summary['transaction_count']}
            """

            await update.message.reply_text(budget_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Sorry, couldn't get budget: {str(e)}")


# ======== EXPENSE FORM HANDLERS ========

async def expense_start_from_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Start expense form from callback."""
    if not is_authorized(query.from_user.id):
        await query.message.reply_text("Sorry, you're not authorized to use this bot.")
        return ConversationHandler.END

    user_id = query.from_user.id
    expense_forms[user_id] = {}

    await query.message.reply_text("💰 *Add Expense*\n\nHow much did you spend?", parse_mode=ParseMode.MARKDOWN)
    return EXPENSE_AMOUNT


async def expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start expense form."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    expense_forms[user_id] = {}
    
    await update.message.reply_text("💰 *Add Expense*\n\nHow much did you spend?", parse_mode=ParseMode.MARKDOWN)
    return EXPENSE_AMOUNT


async def expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense amount input."""
    user_id = update.effective_user.id
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        expense_forms[user_id]['amount'] = amount
        await update.message.reply_text(f"Amount: ${amount:.2f}\n\nWhat did you buy? (description)")
        return EXPENSE_DESCRIPTION
    except ValueError:
        await update.message.reply_text("Please enter a valid amount (e.g., 10.50)")
        return EXPENSE_AMOUNT


async def expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense description input."""
    user_id = update.effective_user.id
    description = update.message.text.strip()
    expense_forms[user_id]['description'] = description
    
    # Get existing categories
    try:
        async with get_session() as session:
            categories = await list_budget_categories(session, str(user_id), type="expense")
            category_names = [cat.name for cat in categories]
    except:
        category_names = []
    
    # Create keyboard with categories
    keyboard = []
    for cat in category_names[:8]:  # Max 8 buttons per row
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"exp_cat_{cat}")])
    keyboard.append([InlineKeyboardButton("Other", callback_data="exp_cat_other")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Description: {description}\n\nSelect category:", reply_markup=reply_markup)
    return EXPENSE_CATEGORY


async def expense_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    category_data = query.data
    
    if category_data == "exp_cat_other":
        await query.message.reply_text("Enter new category name:")
        context.user_data['new_category_mode'] = True
        return EXPENSE_CATEGORY
    else:
        category = category_data.replace("exp_cat_", "")
        expense_forms[user_id]['category'] = category
        context.user_data['new_category_mode'] = False
        
        # Payment method keyboard
        keyboard = [
            [InlineKeyboardButton("💵 Cash", callback_data="exp_pay_cash"),
             InlineKeyboardButton("💳 Card", callback_data="exp_pay_card")],
            [InlineKeyboardButton("📱 Transfer", callback_data="exp_pay_transfer"),
             InlineKeyboardButton("Other", callback_data="exp_pay_other")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"Category: {category}\n\nSelect payment method:", reply_markup=reply_markup)
        return EXPENSE_PAYMENT_METHOD


async def expense_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    payment_data = query.data
    
    payment_map = {
        "exp_pay_cash": "cash",
        "exp_pay_card": "card",
        "exp_pay_transfer": "transfer",
        "exp_pay_other": "other",
    }
    payment_method = payment_map.get(payment_data, "other")
    expense_forms[user_id]['payment_method'] = payment_method
    
    # Date keyboard
    keyboard = [
        [InlineKeyboardButton("📅 Today", callback_data="exp_date_today"),
         InlineKeyboardButton("📆 Yesterday", callback_data="exp_date_yesterday")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"Payment method: {payment_method}\n\nSelect date:", reply_markup=reply_markup)
    return EXPENSE_DATE


async def expense_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle date selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    date_data = query.data
    
    if date_data == "exp_date_today":
        transaction_date = date.today()
    elif date_data == "exp_date_yesterday":
        transaction_date = date.today() - timedelta(days=1)
    else:
        transaction_date = date.today()
    
    expense_forms[user_id]['transaction_date'] = transaction_date
    
    # Show summary and confirm
    form_data = expense_forms[user_id]
    summary = f"""
📋 *Expense Summary*

Amount: ${form_data['amount']:.2f}
Description: {form_data['description']}
Category: {form_data.get('category', 'N/A')}
Payment: {form_data.get('payment_method', 'N/A')}
Date: {form_data['transaction_date']}
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="exp_confirm"),
         InlineKeyboardButton("❌ Cancel", callback_data="exp_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    return EXPENSE_CONFIRM


async def expense_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense confirmation."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "exp_cancel":
        del expense_forms[user_id]
        await query.message.edit_text("Expense cancelled.")
        return ConversationHandler.END
    
    # Save expense
    form_data = expense_forms[user_id]
    
    try:
        async with get_session() as session:
            await add_transaction(
                session=session,
                user_id=str(user_id),
                amount=form_data['amount'],
                type="expense",
                description=form_data['description'],
                transaction_date=form_data['transaction_date'],
                payment_method=form_data.get('payment_method'),
            )
        
        del expense_forms[user_id]
        await query.message.edit_text("✅ Expense saved successfully!")
        return ConversationHandler.END
        
    except Exception as e:
        await query.message.edit_text(f"❌ Error saving expense: {str(e)}")
        return ConversationHandler.END


async def expense_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel expense form."""
    user_id = update.effective_user.id
    if user_id in expense_forms:
        del expense_forms[user_id]
    await update.message.reply_text("Expense form cancelled.")
    return ConversationHandler.END


# ======== INCOME FORM HANDLERS ========

async def income_start_from_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Start income form from callback."""
    if not is_authorized(query.from_user.id):
        await query.message.reply_text("Sorry, you're not authorized to use this bot.")
        return ConversationHandler.END

    user_id = query.from_user.id
    income_forms[user_id] = {}

    await query.message.reply_text("💵 *Add Income*\n\nHow much income?", parse_mode=ParseMode.MARKDOWN)
    return INCOME_AMOUNT


async def income_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start income form."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    income_forms[user_id] = {}
    
    await update.message.reply_text("💵 *Add Income*\n\nHow much income?", parse_mode=ParseMode.MARKDOWN)
    return INCOME_AMOUNT


async def income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income amount input."""
    user_id = update.effective_user.id
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        income_forms[user_id]['amount'] = amount
        await update.message.reply_text(f"Amount: ${amount:.2f}\n\nWhat's the source? (description)")
        return INCOME_DESCRIPTION
    except ValueError:
        await update.message.reply_text("Please enter a valid amount (e.g., 1000.00)")
        return INCOME_AMOUNT


async def income_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income description input."""
    user_id = update.effective_user.id
    description = update.message.text.strip()
    income_forms[user_id]['description'] = description
    
    # Category keyboard
    keyboard = [
        [InlineKeyboardButton("💼 Salary", callback_data="inc_cat_salary"),
         InlineKeyboardButton("🔨 Freelance", callback_data="inc_cat_freelance")],
        [InlineKeyboardButton("🎁 Gift", callback_data="inc_cat_gift"),
         InlineKeyboardButton("📈 Investment", callback_data="inc_cat_investment")],
        [InlineKeyboardButton("Other", callback_data="inc_cat_other")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Description: {description}\n\nSelect category:", reply_markup=reply_markup)
    return INCOME_CATEGORY


async def income_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income category selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    category_data = query.data
    
    category_map = {
        "inc_cat_salary": "Salary",
        "inc_cat_freelance": "Freelance",
        "inc_cat_gift": "Gift",
        "inc_cat_investment": "Investment",
        "inc_cat_other": "Other",
    }
    category = category_map.get(category_data, "Other")
    income_forms[user_id]['category'] = category
    
    # Date keyboard
    keyboard = [
        [InlineKeyboardButton("📅 Today", callback_data="inc_date_today"),
         InlineKeyboardButton("📆 Yesterday", callback_data="inc_date_yesterday")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"Category: {category}\n\nSelect date:", reply_markup=reply_markup)
    return INCOME_DATE


async def income_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income date selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    date_data = query.data
    
    if date_data == "inc_date_today":
        transaction_date = date.today()
    elif date_data == "inc_date_yesterday":
        transaction_date = date.today() - timedelta(days=1)
    else:
        transaction_date = date.today()
    
    income_forms[user_id]['transaction_date'] = transaction_date
    
    # Show summary and confirm
    form_data = income_forms[user_id]
    summary = f"""
📋 *Income Summary*

Amount: ${form_data['amount']:.2f}
Description: {form_data['description']}
Category: {form_data.get('category', 'N/A')}
Date: {form_data['transaction_date']}
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="inc_confirm"),
         InlineKeyboardButton("❌ Cancel", callback_data="inc_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    return INCOME_CONFIRM


async def income_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income confirmation."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "inc_cancel":
        del income_forms[user_id]
        await query.message.edit_text("Income cancelled.")
        return ConversationHandler.END
    
    # Save income
    form_data = income_forms[user_id]
    
    try:
        async with get_session() as session:
            await add_transaction(
                session=session,
                user_id=str(user_id),
                amount=form_data['amount'],
                type="income",
                description=form_data['description'],
                transaction_date=form_data['transaction_date'],
            )
        
        del income_forms[user_id]
        await query.message.edit_text("✅ Income saved successfully!")
        return ConversationHandler.END
        
    except Exception as e:
        await query.message.edit_text(f"❌ Error saving income: {str(e)}")
        return ConversationHandler.END


async def income_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel income form."""
    user_id = update.effective_user.id
    if user_id in income_forms:
        del income_forms[user_id]
    await update.message.reply_text("Income form cancelled.")
    return ConversationHandler.END


# ======== CALLBACK HANDLER FOR INLINE BUTTONS ========

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "chat":
        await query.message.reply_text("You can now chat with me directly! Just send a message.")
    elif callback_data == "add_expense":
        await expense_start_from_callback(query, context)
    elif callback_data == "add_income":
        await income_start_from_callback(query, context)
    elif callback_data == "brief":
        await brief_command_from_callback(query, context)
    elif callback_data == "goals":
        await query.message.reply_text("🎯 Goals feature coming soon!")
    elif callback_data == "search":
        await query.message.reply_text("🔍 Use /search <query> to search your memory")
    elif callback_data == "budget":
        await budget_command_from_callback(query, context)


# ======== CREATE APPLICATION ========

def create_application() -> Application:
    """Create and configure the Telegram bot application."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("brief", brief_command))
    application.add_handler(CommandHandler("budget", budget_command))
    
    # Expense form conversation handler
    expense_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("expense", expense_start)],
        states={
            EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_amount)],
            EXPENSE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_description)],
            EXPENSE_CATEGORY: [CallbackQueryHandler(expense_category_callback, pattern="^exp_cat_")],
            EXPENSE_PAYMENT_METHOD: [CallbackQueryHandler(expense_payment_callback, pattern="^exp_pay_")],
            EXPENSE_DATE: [CallbackQueryHandler(expense_date_callback, pattern="^exp_date_")],
            EXPENSE_CONFIRM: [CallbackQueryHandler(expense_confirm_callback, pattern="^exp_(confirm|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", expense_cancel)],
    )
    application.add_handler(expense_conv_handler)
    
    # Income form conversation handler
    income_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("income", income_start)],
        states={
            INCOME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_amount)],
            INCOME_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_description)],
            INCOME_CATEGORY: [CallbackQueryHandler(income_category_callback, pattern="^inc_cat_")],
            INCOME_DATE: [CallbackQueryHandler(income_date_callback, pattern="^inc_date_")],
            INCOME_CONFIRM: [CallbackQueryHandler(income_confirm_callback, pattern="^inc_(confirm|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", income_cancel)],
    )
    application.add_handler(income_conv_handler)
    
    # General callback handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Chat message handler (must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    
    return application


# ======== WEBHOOK HANDLERS ========

async def handle_webhook(update: dict):
    """Handle incoming webhook update from Telegram."""
    application = create_application()
    async with application:
        await application.process_update(Update.de_json(update, application.bot))


async def send_telegram_message(chat_id: str, text: str):
    """Send a message to a Telegram chat (for brain reminders)."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")
    
    from telegram import Bot
    
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
