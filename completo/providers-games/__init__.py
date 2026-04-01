"""
Base Provider para sistema de scraping de filmes
"""

class BaseProvider:
    """
    Classe base para todos os providers de filmes/séries.
    
    Todos os providers devem herdar desta classe e implementar os métodos necessários.
    """
    
    NOME = None  # Nome do provider (ex: "GoFlixy.lol")
    BASE_URL = None  # URL base do site (ex: "https://goflixy.lol")
    
    @staticmethod
    async def buscar_filme(page, termo_busca):
        """
        Busca filmes no site do provider.
        
        Args:
            page: Instância da página do Playwright
            termo_busca: Termo de busca fornecido pelo usuário
            
        Returns:
            Lista de dicionários com informações dos filmes:
            [
                {
                    "nome": "Nome do Filme",
                    "link": "URL do filme no site",
                    "fonte": "Nome do Provider",
                    "tipo": "FILME" ou "SERIE"
                },
                ...
            ]
        """
        raise NotImplementedError("Método buscar_filme deve ser implementado")
    
    @staticmethod
    async def listar_episodios(page, url_filme):
        """
        Lista episódios de uma série ou retorna informações do filme.
        
        Para filmes: retorna uma lista com um único item (o próprio filme)
        Para séries: retorna lista de episódios disponíveis
        
        Args:
            page: Instância da página do Playwright
            url_filme: URL do filme/série
            
        Returns:
            Lista de episódios:
            [
                {
                    "n": "Nome do episódio ou 'Filme'",
                    "u": "URL do episódio/filme",
                    "num": número do episódio (1 para filmes)
                },
                ...
            ]
        """
        raise NotImplementedError("Método listar_episodios deve ser implementado")
    
    @staticmethod
    async def extrair_video(url_episodio):
        """
        Extrai a URL do vídeo de um episódio/filme.
        
        Este método deve:
        1. Navegar até a página do vídeo
        2. Interceptar requisições de rede ou analisar o HTML
        3. Extrair a URL do stream (M3U8, MP4, etc.)
        
        Args:
            url_episodio: URL da página do episódio/filme
            
        Returns:
            Tupla (video_url, referer_url):
            - video_url: URL direta do stream de vídeo (ou None se falhar)
            - referer_url: URL de referência para passar ao player (ou None)
            
        Exemplo:
            return ("https://cdn.example.com/video.m3u8", "https://example.com/player")
        """
        raise NotImplementedError("Método extrair_video deve ser implementado")


# Exporta a classe base
__all__ = ['BaseProvider']