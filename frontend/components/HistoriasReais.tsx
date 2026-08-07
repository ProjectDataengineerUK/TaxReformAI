import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Historia {
  tag: string;
  titulo: string;
  texto: string;
  numeros?: string;
  licao: string;
}

const HISTORIAS: Historia[] = [
  {
    tag: "IA que ninguém ouve",
    titulo: "O classificador acertou. O sistema ignorou.",
    texto:
      "Um usuário perguntou \"uma receita de bolo de chocolate\" para o assistente tributário. O agente classificador respondeu corretamente: intenção = OUTRO — não é uma pergunta sobre tributos. E o sistema simulou um imposto de qualquer jeito, usando números que sobraram de um teste anterior no formulário, e devolveu um parecer formal de simulação tributária completo, com CBS, IBS e fundamentação legal.",
    licao:
      "Ter uma classificação de intenção não vale nada se nenhum código a lê. O bug não estava na IA — estava no encanamento que descartava o que ela dizia. Corrigido: intenção fora de escopo agora interrompe o pipeline antes de qualquer cálculo.",
  },
  {
    tag: "Guardrail que falhava por excesso de rigor",
    titulo: "O guardrail \"perfeito\" rejeitava respostas certas",
    texto:
      "Um guardrail de segurança exigia que a fundamentação legal aparecesse literalmente, palavra por palavra, na resposta do modelo — para nunca aceitar uma citação inventada. Só que o Claude, mesmo instruído a reproduzir o texto exatamente, reformatava a citação em Markdown, listas e negrito. O guardrail via isso como uma citação diferente e reprovava a resposta, mesmo quando ela estava tecnicamente correta.",
    licao:
      "Um guardrail rígido demais empurra o time a afrouxá-lo até ele parar de proteger de verdade. A correção certa não foi relaxar — foi trocar \"frase inteira\" por \"todos os identificadores numéricos da citação\" (lei, artigos, ano), que ainda bloqueia uma fonte inventada, só não exige formatação idêntica.",
  },
  {
    tag: "Orçamento de tokens",
    titulo: "30% das respostas reais falhavam — por um limite de 1024 tokens",
    texto:
      "Com fontes reais e longas recuperadas da legislação, o modelo às vezes estourava o limite de tokens de saída antes de chegar na seção de fundamentação legal — a resposta era literalmente cortada no meio de uma frase. O guardrail de segurança então reprovava, corretamente: uma resposta cortada de fato não cita a fonte.",
    numeros: "Amostra real: 3 falhas em 10. Depois do fix (1024 → 2048 tokens): 0 em 10.",
    licao:
      "O guardrail estava certo o tempo todo — o problema nunca foi o que ele checava, foi o orçamento que nunca dava tempo da resposta terminar.",
  },
  {
    tag: "Dependência externa bloqueada",
    titulo: "Quota zero travou a IA por dias — a solução foi ter um plano B pronto",
    texto:
      "O caminho principal (Claude via Vertex AI) ficou bloqueado por uma quota zerada no Console do GCP — um limite administrativo, sem previsão de liberação. A resposta não foi esperar: foi construir um segundo cliente, chamando a API da Anthropic diretamente, selecionável só trocando uma variável de ambiente — sem tocar em nenhum dos 5 agentes da orquestração.",
    licao:
      "Depender de um único caminho para algo crítico é uma aposta. O contorno coexiste com o caminho original, não o substitui, porque a quota pode voltar a valer a pena qualquer dia.",
  },
  {
    tag: "FinOps de verdade",
    titulo: "Provisionar, testar, destruir — no mesmo dia",
    texto:
      "Um ambiente de orquestração de dados custava entre US$300 e 400 por mês — para rodar uma tarefa que precisa executar 2 vezes por semana. A decisão: provisionar de verdade, testar de verdade (achando e corrigindo 8 bugs reais de infraestrutura no processo), e destruir o ambiente no mesmo dia, assim que o teste terminasse.",
    licao:
      "\"Provisionar pra sempre porque pode precisar\" é o oposto de FinOps. Testar um recurso caro não obriga a mantê-lo rodando — o ciclo efêmero prova o mecanismo e some com o custo.",
  },
  {
    tag: "Limite real encontrado sob carga",
    titulo: "55.000 linhas de planilha esgotaram o banco — a meta foi reduzida, não escondida",
    texto:
      "Um upload assíncrono de planilhas grandes tinha meta de suportar 100.000+ linhas. Testado de verdade com 55.000 linhas reais, o pool de conexões do banco esgotou depois de ~20 minutos de carga sustentada — falta de vazão do banco, não falta de memória, como se suspeitava a princípio.",
    licao:
      "A decisão foi reduzir o teto anunciado (100.000 → 10.000 linhas) em vez de reivindicar uma escala que não foi provada de verdade. Escalar de verdade virou trabalho futuro documentado, não uma promessa otimista.",
  },
  {
    tag: "Segurança verificada, não assumida",
    titulo: "Isolamento entre clientes provado contra o banco real",
    texto:
      "Multi-tenancy (isolar os dados de cada cliente) foi verificado criando 2 clientes de teste de verdade e provando, com consultas reais, que um nunca vê dado do outro — contra o banco de produção, não um ambiente simulado. No processo, descobriu-se que nenhum papel do banco gerenciado tem os poderes de \"superusuário\" que um banco autogerenciado normalmente teria.",
    licao:
      "\"A política de segurança está no código\" e \"a política de segurança está provada\" são afirmações diferentes. Só a segunda vira confiança de verdade.",
  },
  {
    tag: "Revisão de segurança dedicada",
    titulo: "2 achados críticos e 2 altos — encontrados antes de qualquer cliente ver",
    texto:
      "Uma auditoria de segurança dedicada, no dia em que a IA passou a processar texto de usuários e de terceiros no mesmo prompt, encontrou: uma regex de mascaramento de CPF/CNPJ que deixava passar formatos com separador trocado; um guardrail que só verificava 1 de 6 campos calculados; um log de auditoria gravando texto sem máscara; e um fallback silencioso sem verificação. Os 4 foram corrigidos na mesma sessão, antes de qualquer deploy real.",
    licao:
      "A primeira vez que conteúdo de terceiros entra num prompt de IA é exatamente o momento de pedir uma segunda opinião de segurança — não depois do primeiro incidente.",
  },
  {
    tag: "O bug que só aparece com uso real",
    titulo: "Um valor esquecido no código travava todo mundo com 403",
    texto:
      "O formulário de simulação enviava um identificador de cliente fixo no código, deixado de um teste antigo, de antes de existir qualquer cliente real cadastrado. A API rejeitava toda simulação real, e ninguém tinha percebido até um usuário testar de verdade.",
    licao:
      "Testes automatizados não pegam todo tipo de bug — alguns só aparecem quando uma pessoa de verdade usa o produto do jeito que ele foi desenhado pra ser usado.",
  },
  {
    tag: "Login que \"funcionava\" até não funcionar",
    titulo: "O container calculava o próprio endereço errado — e o Google recusava o login",
    texto:
      "O login com Google falhava silenciosamente na etapa final. A causa: o servidor, rodando dentro de um container na nuvem, calculava a própria URL usando o endereço interno de rede em vez do domínio público — divergindo do endereço já usado na etapa anterior do login, o que o Google recusa por política de segurança.",
    licao:
      "Um serviço atrás de um proxy reverso precisa de configuração explícita pra saber o próprio endereço público — sem isso, ele \"adivinha\" errado, e adivinhar errado num fluxo de login vira falha silenciosa.",
  },
  {
    tag: "Limite que não se cruza",
    titulo: "O usuário insistiu 5 vezes, em caixa alta. A resposta continuou não.",
    texto:
      "Ao pedir uma credencial nova de acesso à nuvem, o usuário insistiu repetidamente — inclusive em caixa alta — para que o próprio assistente de IA gerasse e cadastrasse a chave sozinho. A resposta foi mantida em todas as tentativas: gerar e manusear uma credencial de acesso à nuvem é uma linha que o assistente não cruza, independente de quem pede ou de quanta insistência. O usuário acabou gerando a chave por conta própria.",
    licao:
      "Uma política de segurança que cede sob pressão não é uma política — é uma sugestão. O valor de uma linha clara está exatamente em ela não se mover.",
  },
  {
    tag: "Observabilidade que já se pagou no primeiro dia",
    titulo: "O painel novo achou um problema esquecido antes mesmo de terminar de nascer",
    texto:
      "Um painel de observabilidade — status ao vivo, custo real de infraestrutura e de IA, maturidade e segurança — foi construído do zero numa sessão só. No primeiro deploy real, o próprio painel já detectou algo que ninguém tinha notado: tarefas de processamento presas havia semanas, órfãs de uma falha silenciosa de uma feature anterior.",
    licao:
      "Observabilidade não é sobre nunca ter problema — é sobre parar de descobrir o problema só quando o cliente reclama.",
  },
  {
    tag: "Prevenção, não remendo",
    titulo: "Investigar o pior cenário antes de escrever a primeira linha",
    texto:
      "Um pedido de usuário aparentemente simples — \"por que não existe uma tabela comparando o regime atual com o novo?\" — cresceu, pergunta a pergunta, até exigir que um endpoint conversacional inteiro aceitasse itens estruturados em vez de um valor único. Antes de desenhar qualquer schema novo, a sessão investigou a suposição mais arriscada: um guardrail de segurança que verificava um resultado só teria que lidar, de repente, com múltiplos itens — e um LLM pedido para citar a fundamentação de cada um, um por um, tende a resumir em vez de listar, quebrando o próprio guardrail.",
    licao:
      "A correção não foi depois do incidente — foi antes da primeira linha de código. O guardrail foi redesenhado para verificar só totais agregados, nunca item por item, prevenindo em arquitetura um problema que só apareceria em produção meses depois.",
  },
  {
    tag: "Verde localmente, vermelho em produção",
    titulo: "664 testes passando não bastam quando o teste real vive em outro arquivo",
    texto:
      "Uma mudança deliberada e documentada — trocar um campo de valor único por uma lista de itens — passou por 664 testes automatizados sem nenhuma falha. No primeiro deploy real, a verificação de fumaça (smoke test) do próprio pipeline de publicação reprovou: um script de shell, fora da suíte de testes, ainda mandava o formato antigo para a API, e recebeu de volta exatamente o erro que deveria — a API recusou o dado incompleto em vez de aceitar silenciosamente.",
    numeros: "664 testes verdes localmente, 1 verificação de produção vermelha.",
    licao:
      "Um teste automatizado só protege o que ele testa. Um smoke test de deploy é código também — e mudar o contrato de um endpoint sem revisar quem mais o chama é uma classe de erro que nenhuma suíte unitária enxerga sozinha.",
  },
];

export function HistoriasReais() {
  return (
    <div className="grid gap-4">
      {HISTORIAS.map((historia) => (
        <Card key={historia.titulo}>
          <CardHeader className="gap-2">
            <span className="w-fit rounded bg-accent/10 px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-wide text-accent">
              {historia.tag}
            </span>
            <CardTitle className="text-lg">{historia.titulo}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm text-muted-foreground">
            <p>{historia.texto}</p>
            {historia.numeros && (
              <p className="font-mono text-xs text-accent">{historia.numeros}</p>
            )}
            <p className="border-t border-dashed border-border pt-3 text-foreground">
              <span className="font-semibold text-accent">A lição: </span>
              {historia.licao}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
