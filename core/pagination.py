from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PadraoPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500

    def get_paginated_response(self, data):
        return Response(
            {
                "total": self.page.paginator.count,
                "pagina_atual": self.page.number,
                "total_paginas": self.page.paginator.num_pages,
                "proxima": self.get_next_link(),
                "anterior": self.get_previous_link(),
                "resultados": data,
            }
        )
