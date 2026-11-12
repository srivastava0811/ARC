import Image from "next/image";
import Link from "next/link";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  FileText,
  Github,
  Layers3,
  Monitor,
  ScanSearch,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import "./arc-landing.css";

const stages = [
  { number: "01", name: "Planner", icon: Layers3, copy: "Turn a request into clear requirements. Quantity, budget, and the details that matter." },
  { number: "02", name: "Researcher", icon: ScanSearch, copy: "Discover products and gather the evidence behind each option." },
  { number: "03", name: "Evaluator", icon: SlidersHorizontal, copy: "Check your constraints, compare eligible options, and explain the tradeoffs." },
  { number: "04", name: "Reporter", icon: FileText, copy: "Bring the recommendations together so you can make the final call." },
];

export function ArcLanding() {
  return (
    <div className="arc-landing">
      <a className="landing-skip" href="#main">Skip to content</a>
      <header className="landing-nav landing-container">
        <Link href="/" className="landing-brand" aria-label="ARC home">
          <Image src="/icon.png" width={34} height={34} alt="" priority />
          <span>ARC<span className="landing-brand-dot">.</span></span>
        </Link>
        <nav aria-label="Main navigation" className="landing-nav-links">
          <a href="#workflow">How it works</a>
          <a href="#approval">Your control</a>
          <a href="https://github.com/srivastava0811/ARC" target="_blank" rel="noreferrer" className="landing-github" aria-label="ARC on GitHub (opens in a new tab)"><Github size={17} aria-hidden="true" /> <span>GitHub</span></a>
        </nav>
        <Link href="/workspace" className="landing-button landing-button-small">Launch ARC <ArrowUpRight size={15} aria-hidden="true" /></Link>
      </header>

      <main id="main">
        <section className="landing-hero landing-container" aria-labelledby="landing-title">
          <div className="landing-hero-copy">
            <p className="landing-eyebrow"><span className="landing-status-dot" /> THE AUTONOMOUS RESOURCE COORDINATOR</p>
            <h1 id="landing-title">From &ldquo;we need&rdquo;<br />to <span>approved.</span></h1>
            <p className="landing-hero-description">Less searching. Clearer decisions. Describe what your team needs, compare the evidence, and approve the next step.</p>
            <div className="landing-hero-actions">
              <Link href="/workspace" className="landing-button">Open your workspace <ArrowRight size={18} aria-hidden="true" /></Link>
              <a href="#workflow" className="landing-text-link">Meet the four agents <ArrowDown size={15} aria-hidden="true" /></a>
            </div>
            <p className="landing-hero-note"><ShieldCheck size={14} aria-hidden="true" /> Agents do the groundwork. You approve the payment.</p>
          </div>

          <div className="landing-preview" aria-label="Illustrative procurement workflow using synthetic demo products">
            <div className="landing-preview-top"><span><span className="landing-status-dot" /> WORKSPACE PREVIEW</span><span>001 / PROCUREMENT</span></div>
            <div className="landing-request"><span className="landing-avatar">YOU</span><p>Three 27-inch monitors.<br /><strong>Under $600 total.</strong></p><ArrowUpRight size={19} aria-hidden="true" /></div>
            <div className="landing-preview-stages">
              {stages.map((stage) => <div key={stage.name}><span><Check size={12} strokeWidth={3} aria-hidden="true" /></span>{stage.name}</div>)}
            </div>
            <div className="landing-preview-product">
              <div className="landing-monitor-art" aria-hidden="true"><div className="landing-monitor-screen"><span /><span /><span /></div><div className="landing-monitor-neck" /><div className="landing-monitor-foot" /></div>
              <div className="landing-preview-product-copy"><span className="landing-product-label"><CheckCheck size={13} aria-hidden="true" /> WITHIN YOUR BUDGET</span><h2>StudioView 27 4K</h2><p>27-inch display · 4K UHD</p><div className="landing-product-price"><strong>$567<span> / 3 units</span></strong><span>$189 each</span></div></div>
            </div>
            <div className="landing-approval-preview"><span className="landing-approval-icon"><ShieldCheck size={19} aria-hidden="true" /></span><div><strong>Your approval comes next.</strong><span>Review the choice before Sandbox checkout.</span></div><ArrowRight size={17} aria-hidden="true" /></div>
            <div className="landing-preview-caption"><span>Illustrative workflow · synthetic demo catalog</span><span>USD</span></div>
          </div>
        </section>

        <section className="landing-integrations landing-container" aria-label="Integrations">
          <span className="landing-section-label">CONNECTED WHERE IT COUNTS</span>
          <div><span>Gemini<small>AI explanations</small></span><span>Channel3<small>Product discovery</small></span><span className="landing-paypal-word">PayPal<small>Sandbox payments</small></span><span>PostgreSQL<small>Persistent history</small></span></div>
        </section>

        <section id="workflow" className="landing-workflow landing-container" aria-labelledby="workflow-title">
          <div className="landing-section-heading"><div><p className="landing-eyebrow">A CLEAR PATH FROM INTENT TO ACTION</p><h2 id="workflow-title">Four specialists.<br />One considered decision.</h2></div><p>Each stage has a job. Together, they turn an open-ended request into options you can actually evaluate.</p></div>
          <div className="landing-agent-grid">
            {stages.map((stage) => <article className="landing-agent" key={stage.name}><div className="landing-agent-top"><stage.icon size={24} strokeWidth={1.5} aria-hidden="true" /><span>{stage.number}</span></div><h3>{stage.name}</h3><p>{stage.copy}</p></article>)}
          </div>
          <p className="landing-workflow-note">Deterministic requirement checks. Optional Gemini explanations and summaries. A clear view of every stage.</p>
        </section>

        <section id="approval" className="landing-control landing-container" aria-labelledby="approval-title">
          <div className="landing-control-copy"><p className="landing-eyebrow">AUTOMATION WITH A HUMAN CHECKPOINT</p><h2 id="approval-title">The final say<br />stays with you.</h2><p>Inspect the recommendation, check the quantity and total, then choose whether to proceed. PayPal Sandbox handles buyer approval; ARC confirms the capture and saves the receipt.</p><Link href="/workspace" className="landing-text-link">Try a procurement request <ArrowUpRight size={16} aria-hidden="true" /></Link></div>
          <div className="landing-control-list">
            <div><span>01</span><section><h3>Evidence before action</h3><p>See product details, eligibility, and tradeoffs before you select.</p></section><ScanSearch size={21} aria-hidden="true" /></div>
            <div><span>02</span><section><h3>Approval before payment</h3><p>Review the total and authorize checkout with a Sandbox buyer.</p></section><ShieldCheck size={21} aria-hidden="true" /></div>
            <div><span>03</span><section><h3>A record after the decision</h3><p>Return to saved requests, reports, and completed payment receipts.</p></section><FileText size={21} aria-hidden="true" /></div>
          </div>
        </section>

        <section className="landing-final landing-container" aria-labelledby="landing-final-title"><div><p className="landing-eyebrow">START WITH WHAT YOU NEED</p><h2 id="landing-final-title">Your next request,<br />with a little less work.</h2></div><div><Link href="/workspace" className="landing-button">Launch ARC <ArrowUpRight size={18} aria-hidden="true" /></Link><p><Monitor size={14} aria-hidden="true" /> Monitors, keyboards, and mice.</p></div></section>
      </main>

      <footer className="landing-footer landing-container"><div><Link href="/" className="landing-footer-brand">ARC.</Link><span>From intent to transaction.</span></div><p>Built for the PayPal AI Hackathon.<br />Sandbox payments use test funds. No merchant fulfillment.</p><a href="https://github.com/srivastava0811/ARC#readme" target="_blank" rel="noreferrer">Source &amp; setup <ArrowUpRight size={14} aria-hidden="true" /></a></footer>
    </div>
  );
}
