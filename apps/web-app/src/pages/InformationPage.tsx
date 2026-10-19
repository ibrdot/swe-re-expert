import { useEffect } from 'react';
import { Link, useLocation } from 'react-router';
import pages from '../data/informationPages.json';
import { usePageMeta } from '../hooks/usePageMeta';
import './InformationPage.css';

export default function InformationPage(): React.ReactElement {
  const { pathname, hash } = useLocation();
  const page = pages.find((entry) => entry.path === `${pathname.replace(/\/$/, '')}/`)!;
  useEffect(() => {
    if (/^#section-\d+$/.test(hash)) document.getElementById(hash.slice(1))?.scrollIntoView();
    else window.scrollTo(0, 0);
  }, [pathname, hash]);
  usePageMeta({
    title: `${page.title} | Agentic Awesome Skills`,
    description: page.description,
    canonicalPath: page.path,
    robots: 'index, follow',
    jsonLd: (canonicalUrl) => [{
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: page.title,
      headline: page.title,
      description: page.description,
      url: canonicalUrl,
      mainEntityOfPage: canonicalUrl,
      isPartOf: {
        '@type': 'WebSite',
        name: 'Agentic Awesome Skills',
        url: canonicalUrl.replace(/[^/]+\/?$/u, ''),
      },
    }],
  });
  return <div className="information-page">
    <header><p className="information-page__eyebrow">{page.title}</p><h1>{page.intro}</h1><p className="information-page__lede">{page.lede}</p></header>
    <nav className="information-page__outline" aria-label="On this page">{page.sections.map((section, index) => <a key={section.title} href={`${page.path}#section-${index}`}>{section.title}</a>)}</nav>
    <div className="information-page__sections">{page.sections.map((section, index) => <section key={section.title} id={`section-${index}`} aria-labelledby={`heading-${index}`}>
      <h2 id={`heading-${index}`}>{section.title}</h2><p>{section.body}</p>
      <div className="information-page__links">{section.links.map((link) => link.href.startsWith('/') ? <Link key={link.href} to={link.href}>{link.label} →</Link> : <a key={link.href} href={link.href}>{link.label} ↗</a>)}</div>
    </section>)}</div>
  </div>;
}
