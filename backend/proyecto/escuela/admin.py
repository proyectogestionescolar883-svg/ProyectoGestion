from django.contrib import admin

from escuela.models import (
    Acta,
    ActaAlumno,
    ActaCurso,
    Alumno,
    Asistencia,
    Calificacion,
    CicloLectivo,
    Curso,
    CursoMateria,
    DiagnosticoGrupal,
    Directivo,
    Docente,
    EstadoAsistencia,
    Horario,
    InscripcionMateria,
    Materia,
    Notificacion,
    PadreTutor,
    PeriodoEvaluacion,
    Planificacion,
    Preceptor,
    Rol,
    TipoActa,
    Usuario,
    UsuarioRol,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'usuario', 'estado', 'eliminado')
    search_fields = ('usuario',)
    exclude = ('contrasena',)
    readonly_fields = ('ultimo_acceso',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id_rol', 'nombre_rol')

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()
        return ('id_rol', 'nombre_rol')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(UsuarioRol)
class UsuarioRolAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'id_rol')
    raw_id_fields = ('id_usuario', 'id_rol')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('id_calificacion', 'id_alumno', 'id_curso_materia', 'nota_numerica', 'estado')
    readonly_fields = ('fecha_carga',)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('fecha_carga',)
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


admin.site.register(Alumno)
admin.site.register(Docente)
admin.site.register(Preceptor)
admin.site.register(Directivo)
admin.site.register(PadreTutor)
admin.site.register(CicloLectivo)
admin.site.register(Curso)
admin.site.register(Materia)
admin.site.register(CursoMateria)
admin.site.register(Horario)
admin.site.register(InscripcionMateria)
admin.site.register(PeriodoEvaluacion)
admin.site.register(EstadoAsistencia)
admin.site.register(Asistencia)
admin.site.register(TipoActa)
admin.site.register(Acta)
admin.site.register(ActaAlumno)
admin.site.register(ActaCurso)
admin.site.register(Planificacion)
admin.site.register(DiagnosticoGrupal)
admin.site.register(Notificacion)
