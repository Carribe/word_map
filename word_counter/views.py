from .forms import UploadFileForm
from django.shortcuts import render
from word_counter.tasks import process_word_file_task

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']  # Получаем объект UploadedFile
            selected_region_id = form.cleaned_data['region'].ogc_fid  # Получаем ID выбранного региона

            # Читаем содержимое файла
            file_content = uploaded_file.read()

            file_name = uploaded_file.name  # Получаем имя файла
            process_word_file_task.delay(file_content, file_name, selected_region_id)  # Передаем содержимое файла, имя файла и selected_region_id

            processed_data = "Файл успешно отправлен на обработку."
            return render(request, 'word_counter/upload_success.html', {'processed_data': processed_data})
    else:
        form = UploadFileForm()
        return render(request, 'word_counter/upload_file.html', {'form': form})