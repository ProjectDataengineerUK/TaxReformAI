from dataclasses import dataclass, field

NIVEIS_HIERARQUICOS = ("LIVRO", "TITULO", "CAPITULO", "SECAO", "SUBSECAO")


@dataclass
class Alinea:
    letra: str  # ex: "a"
    texto: str


@dataclass
class Inciso:
    numero: str  # ex: "II"
    texto: str
    alineas: list[Alinea] = field(default_factory=list)


@dataclass
class Paragrafo:
    numero: str  # ex: "2º" ou "único"
    texto: str
    incisos: list[Inciso] = field(default_factory=list)


@dataclass
class Artigo:
    numero: str  # ex: "18"
    texto: str
    paragrafos: list[Paragrafo] = field(default_factory=list)
    incisos: list[Inciso] = field(default_factory=list)  # incisos direto no caput


@dataclass
class Secao:
    """Nó genérico para Livro/Título/Capítulo/Seção/Subseção.

    A LC 214/2025 real usa 5 níveis de cabeçalho (Livro > Título > Capítulo >
    Seção > Subseção), mais do que os 2 níveis (Título/Capítulo) descritos na
    seção 4.3 do blueprint. Um nó recursivo com `nivel` generaliza para
    qualquer profundidade sem precisar de uma dataclass por nível.
    """

    nivel: str  # um de NIVEIS_HIERARQUICOS
    numero: str  # ex: "I"
    titulo: str  # ex: "DISPOSIÇÕES PRELIMINARES"
    subsecoes: list["Secao"] = field(default_factory=list)
    artigos: list[Artigo] = field(default_factory=list)


@dataclass
class Lei:
    documento_id: str  # ex: "LCP_214_2025"
    titulo: str
    fonte_url: str
    secoes: list[Secao] = field(default_factory=list)
    artigos_soltos: list[Artigo] = field(default_factory=list)
