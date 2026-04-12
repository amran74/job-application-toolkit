import streamlit as st


def inject_global_css():
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b1020;
            --bg-2: #0f172a;
            --panel: rgba(17, 24, 39, 0.78);
            --panel-strong: rgba(15, 23, 42, 0.92);
            --border: rgba(148, 163, 184, 0.14);
            --text: #eef2ff;
            --muted: #9fb0c8;
            --soft: #7f8ea8;
            --accent: #7c8cff;
            --accent-2: #9c88ff;
        }

        html, body, [class*="css"] {
            color: var(--text);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(124,140,255,0.12), transparent 26%),
                radial-gradient(circle at top right, rgba(156,136,255,0.10), transparent 24%),
                linear-gradient(180deg, #08101f 0%, #0b1020 100%);
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
            height: 0rem;
        }

        div[data-testid="stDecoration"] {
            display: none;
        }

        .block-container {
            max-width: 1180px;
            padding-top: 0.85rem !important;
            padding-bottom: 2rem;
        }

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(17, 24, 39, 0.98) 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.10);
        }

        section[data-testid="stSidebar"] * {
            color: #dbe7ff !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            padding-top: 0.15rem;
        }

        section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            border-radius: 14px;
            border: 1px solid transparent;
            background: transparent;
            padding-top: 0.48rem !important;
            padding-bottom: 0.48rem !important;
            transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
        }

        section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]:hover,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
            background: rgba(255,255,255,0.04);
            border-color: rgba(255,255,255,0.06);
            transform: translateX(1px);
        }

        section[data-testid="stSidebar"] a[aria-current="page"] {
            background: rgba(255,255,255,0.08) !important;
            border-color: rgba(255,255,255,0.10) !important;
        }

        .sidebar-brand {
            margin-top: 0.15rem;
            margin-bottom: 0.7rem;
            padding: 0.8rem 0.85rem 0.85rem 0.85rem;
            border-radius: 18px;
            background:
                linear-gradient(135deg, rgba(124,140,255,0.16), rgba(156,136,255,0.08)),
                rgba(255,255,255,0.02);
            border: 1px solid rgba(124,140,255,0.14);
        }

        .sidebar-brand-title {
            font-size: 1.02rem;
            font-weight: 800;
            color: #f8fbff;
            line-height: 1.15;
            margin-bottom: 0.18rem;
        }

        .sidebar-brand-subtitle {
            font-size: 0.79rem;
            color: #a9b7cf;
            line-height: 1.4;
        }

        .app-hero {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(135deg, rgba(124,140,255,0.14), rgba(156,136,255,0.08)),
                linear-gradient(180deg, rgba(17,24,39,0.84), rgba(15,23,42,0.92));
            border: 1px solid rgba(124,140,255,0.14);
            border-radius: 24px;
            padding: 1.15rem 1.25rem 1.1rem 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.22);
        }

        .app-eyebrow {
            font-size: 0.73rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #b8c5e0;
            margin-bottom: 0.28rem;
        }

        .app-title {
            font-size: 2rem;
            font-weight: 840;
            color: #f8fbff;
            line-height: 1.05;
            margin-bottom: 0.32rem;
        }

        .app-subtitle {
            font-size: 0.97rem;
            color: #b1bfd6;
            line-height: 1.52;
            max-width: 860px;
        }

        .section-title {
            font-size: 1rem;
            font-weight: 760;
            color: #edf2ff;
            margin-top: 0.15rem;
            margin-bottom: 0.58rem;
        }

        .soft-card {
            background:
                linear-gradient(180deg, rgba(17,24,39,0.70), rgba(15,23,42,0.78));
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 0.95rem 1rem 0.9rem 1rem;
            box-shadow: 0 14px 30px rgba(0,0,0,0.18);
            margin-bottom: 0.75rem;
        }

        .soft-card-title {
            font-size: 0.96rem;
            font-weight: 760;
            color: #f7faff;
            margin-bottom: 0.28rem;
        }

        .soft-card-body {
            font-size: 0.91rem;
            color: #aebcd3;
            line-height: 1.52;
        }

        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.46rem;
            margin-top: 0.1rem;
            margin-bottom: 0.18rem;
        }

        .badge-pill {
            display: inline-block;
            padding: 0.28rem 0.6rem;
            border-radius: 999px;
            background: rgba(124,140,255,0.10);
            border: 1px solid rgba(124,140,255,0.16);
            color: #dce6ff;
            font-size: 0.76rem;
            font-weight: 650;
        }

        .quick-link-card {
            background:
                linear-gradient(180deg, rgba(17,24,39,0.72), rgba(15,23,42,0.80));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            box-shadow: 0 12px 28px rgba(0,0,0,0.16);
            margin-bottom: 0.65rem;
        }

        .quick-link-title {
            font-size: 0.94rem;
            font-weight: 760;
            color: #f7faff;
            margin-bottom: 0.18rem;
        }

        .quick-link-desc {
            font-size: 0.84rem;
            color: #a6b4cb;
            line-height: 1.45;
        }

        .table-caption {
            font-size: 0.82rem;
            color: #8190a8;
            margin-top: -0.08rem;
            margin-bottom: 0.45rem;
        }

        .form-shell {
            background:
                linear-gradient(180deg, rgba(17,24,39,0.70), rgba(15,23,42,0.78));
            border: 1px solid rgba(148,163,184,0.14);
            border-radius: 22px;
            padding: 1.05rem 1.05rem 0.9rem 1.05rem;
            box-shadow: 0 14px 30px rgba(0,0,0,0.18);
        }

        div[data-testid="stMetric"] {
            background:
                linear-gradient(180deg, rgba(17,24,39,0.78), rgba(15,23,42,0.86));
            border: 1px solid rgba(148,163,184,0.14);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            box-shadow: 0 12px 28px rgba(0,0,0,0.16);
        }

        .stDataFrame, .stAlert, .stExpander {
            border-radius: 16px;
        }

        button[kind="primary"] {
            border-radius: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand():
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-title">Job Application Toolkit</div>
                <div class="sidebar-brand-subtitle">Structured job search workflow, bilingual CV generation, reusable content blocks, and version history.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_header(title: str, subtitle: str, eyebrow: str = "Job Application Toolkit"):
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="app-eyebrow">{eyebrow}</div>
            <div class="app-title">{title}</div>
            <div class="app-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def soft_card(title: str, body: str):
    st.markdown(
        f"""
        <div class="soft-card">
            <div class="soft-card-title">{title}</div>
            <div class="soft-card-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_row(items):
    pills = "".join([f'<span class="badge-pill">{item}</span>' for item in items if str(item).strip()])
    st.markdown(f'<div class="badge-row">{pills}</div>', unsafe_allow_html=True)


def quick_link_card(title: str, desc: str):
    st.markdown(
        f"""
        <div class="quick-link-card">
            <div class="quick-link-title">{title}</div>
            <div class="quick-link-desc">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def form_shell_open():
    st.markdown('<div class="form-shell">', unsafe_allow_html=True)


def form_shell_close():
    st.markdown('</div>', unsafe_allow_html=True)
