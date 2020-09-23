import 'firebase/auth';
/**
 * The project service encapsulates all backend api calls for performing CRUD operations on project data
 */
export const projectServices = {
    getProjectNames,
}

function getProjectNames(firebase: any) {
   const requestOptions = {
       method: 'GET',
       headers: { 'Content-Type': 'application/json' },
   };
   var token = localStorage.getItem('user-token');

   firebase.firebase.auth.currentUser.getIdToken().then((idToken: string) =>{
    if(token != idToken){
        console.log(firebase.firebase.auth.currentUser.getIdToken() + " not equal");
        localStorage.setItem('user-token',idToken)
    }else{
        console.log("still the same token,not refreshed")
    }
   })
  
   return fetch(process.env.REACT_APP_API_URL + '/projects/all?id_token=' + localStorage.getItem('user-token'), requestOptions) // TODO:config.apiUrl
       .then(handleResponse)
       .then(data => {
           return data.projects
       })
}

function handleResponse(response: { text: () => Promise<any>; ok: any; status: number; statusText: any; }) {
   return response.text().then((text: string) => {
       const data = text && JSON.parse(text);
       if (!response.ok) {
           const error = (data && data.message) || response.statusText;
           return Promise.reject(error);
       }

       return data;
   });
}