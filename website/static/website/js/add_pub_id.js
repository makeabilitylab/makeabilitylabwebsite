// add_pub_id.js
document.addEventListener('DOMContentLoaded', function() {
  function updateLinkWithPublicationId(elementId, publicationId) {
    const linkElement = document.getElementById(elementId);
    if (linkElement && publicationId) {
        const url = new URL(linkElement.href);
        url.searchParams.append('publication_id', publicationId);
        linkElement.href = url.toString();
    }
  }

  //const publicationId = "{{ publication_id }}";
  console.log(`Updating links with publication id ${publicationId}`);
  updateLinkWithPublicationId('add_id_talk', publicationId);
  updateLinkWithPublicationId('add_id_video', publicationId);
});